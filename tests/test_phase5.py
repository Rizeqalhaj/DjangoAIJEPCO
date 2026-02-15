"""
Phase 5 — Investigation & Plan Engine Tests.

Tests enhanced plan services, RAG retriever fallback, RAG ingestion,
notification tasks, Celery beat schedule, and ingest management command.

All external dependencies (ChromaDB, sentence-transformers, Twilio) are mocked.
"""

from datetime import timedelta
from unittest.mock import patch, MagicMock, PropertyMock

from django.test import TestCase
from django.utils import timezone

from accounts.models import Subscriber
from meter.models import MeterReading
from meter.generator import generate_meter_data
from plans.models import OptimizationPlan, PlanCheckpoint


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_subscriber(**kwargs):
    defaults = {
        "subscription_number": "01-500001-01",
        "phone_number": "+962795000001",
        "name": "Phase5 Test User",
        "area": "Sweifieh",
        "tariff_category": "residential",
        "has_ev": True,
        "is_verified": True,
        "language": "en",
    }
    defaults.update(kwargs)
    return Subscriber.objects.create(**defaults)


def _seed_readings(subscriber, days=14):
    readings = generate_meter_data(subscriber, "ev_peak_charger", days=days)
    MeterReading.objects.bulk_create(readings, batch_size=1000)


def _create_plan(subscriber, **kwargs):
    """Create a plan with sensible defaults for testing."""
    from plans.services import create_optimization_plan
    tool_input = {
        "detected_pattern": "High peak consumption 7PM-11PM",
        "user_hypothesis": "EV charging during peak",
        "plan_summary": "Shift EV charging to off-peak hours",
        "actions": [
            {
                "action": "Schedule EV charging 1AM-5AM",
                "expected_impact_kwh": 5.0,
                "expected_savings_fils_per_day": 1456,
            }
        ],
        "monitoring_days": 7,
    }
    tool_input.update(kwargs)
    return create_optimization_plan(subscriber, tool_input)


# ---------------------------------------------------------------------------
# A. Enhanced Plan Services Tests
# ---------------------------------------------------------------------------

class EnhancedPlanServicesTest(TestCase):
    """Test enhanced check_progress with PlanCheckpoint and savings."""

    def setUp(self):
        self.sub = _create_subscriber()
        _seed_readings(self.sub, days=14)
        self.plan = _create_plan(self.sub)

    def test_check_progress_returns_all_keys(self):
        from plans.services import check_progress
        result = check_progress(self.sub, self.plan.id)
        # Original keys
        self.assertIn("plan_id", result)
        self.assertIn("plan_summary", result)
        self.assertIn("status", result)
        self.assertIn("baseline_daily_kwh", result)
        self.assertIn("current_daily_kwh", result)
        self.assertIn("change_percent", result)
        self.assertIn("on_track", result)
        self.assertIn("days_monitored", result)
        self.assertIn("verify_after_date", result)
        # New keys
        self.assertIn("is_improving", result)
        self.assertIn("ready_for_verification", result)
        self.assertIn("estimated_monthly_savings_fils", result)
        self.assertIn("estimated_monthly_savings_jod", result)

    def test_check_progress_creates_checkpoint(self):
        from plans.services import check_progress
        self.assertEqual(PlanCheckpoint.objects.count(), 0)
        check_progress(self.sub, self.plan.id)
        self.assertEqual(PlanCheckpoint.objects.count(), 1)

    def test_multiple_check_progress_creates_multiple_checkpoints(self):
        from plans.services import check_progress
        check_progress(self.sub, self.plan.id)
        check_progress(self.sub, self.plan.id)
        check_progress(self.sub, self.plan.id)
        self.assertEqual(PlanCheckpoint.objects.count(), 3)

    def test_checkpoint_has_correct_data(self):
        from plans.services import check_progress
        result = check_progress(self.sub, self.plan.id)
        cp = PlanCheckpoint.objects.first()
        self.assertEqual(cp.plan, self.plan)
        self.assertEqual(cp.check_date, timezone.now().date())
        self.assertEqual(cp.avg_daily_kwh, result["current_daily_kwh"])
        self.assertEqual(cp.change_vs_baseline_percent, result["change_percent"])

    def test_is_improving_when_consumption_decreases(self):
        from plans.services import check_progress
        result = check_progress(self.sub, self.plan.id)
        if result["change_percent"] < 0:
            self.assertTrue(result["is_improving"])
        else:
            self.assertFalse(result["is_improving"])

    def test_ready_for_verification_before_date(self):
        from plans.services import check_progress
        self.plan.verify_after_date = timezone.now().date() + timedelta(days=30)
        self.plan.save()
        result = check_progress(self.sub, self.plan.id)
        self.assertFalse(result["ready_for_verification"])

    def test_ready_for_verification_after_date(self):
        from plans.services import check_progress
        self.plan.verify_after_date = timezone.now().date() - timedelta(days=1)
        self.plan.save()
        result = check_progress(self.sub, self.plan.id)
        self.assertTrue(result["ready_for_verification"])

    def test_savings_are_numeric(self):
        from plans.services import check_progress
        result = check_progress(self.sub, self.plan.id)
        self.assertIsInstance(result["estimated_monthly_savings_fils"], int)
        self.assertIsInstance(result["estimated_monthly_savings_jod"], float)

    def test_check_progress_nonexistent_plan(self):
        from plans.services import check_progress
        result = check_progress(self.sub, 99999)
        self.assertIn("error", result)

    def test_create_plan_stores_monitoring_period(self):
        plan = _create_plan(
            _create_subscriber(
                subscription_number="01-500099-01",
                phone_number="+962795000099",
            ),
            monitoring_days=14,
        )
        self.assertEqual(plan.plan_details["monitoring_period_days"], 14)


# ---------------------------------------------------------------------------
# B. Plan Checkpoint Creation Tests
# ---------------------------------------------------------------------------

class PlanCheckpointCreationTest(TestCase):
    """Test PlanCheckpoint model records created by check_progress."""

    def setUp(self):
        self.sub = _create_subscriber(
            subscription_number="01-500002-01",
            phone_number="+962795000002",
        )
        _seed_readings(self.sub, days=14)
        self.plan = _create_plan(self.sub)

    def test_checkpoint_linked_to_plan(self):
        from plans.services import check_progress
        check_progress(self.sub, self.plan.id)
        cp = PlanCheckpoint.objects.first()
        self.assertEqual(cp.plan_id, self.plan.id)

    def test_checkpoint_has_peak_offpeak(self):
        from plans.services import check_progress
        check_progress(self.sub, self.plan.id)
        cp = PlanCheckpoint.objects.first()
        self.assertIsNotNone(cp.avg_peak_kwh)
        self.assertIsNotNone(cp.avg_offpeak_kwh)

    def test_checkpoint_has_cost_estimate(self):
        from plans.services import check_progress
        check_progress(self.sub, self.plan.id)
        cp = PlanCheckpoint.objects.first()
        self.assertIsInstance(cp.estimated_cost_fils_per_day, int)

    def test_checkpoint_change_matches_result(self):
        from plans.services import check_progress
        result = check_progress(self.sub, self.plan.id)
        cp = PlanCheckpoint.objects.first()
        self.assertAlmostEqual(cp.change_vs_baseline_percent, result["change_percent"], places=1)

    def test_checkpoint_ordering(self):
        from plans.services import check_progress
        check_progress(self.sub, self.plan.id)
        check_progress(self.sub, self.plan.id)
        cps = list(PlanCheckpoint.objects.all())
        self.assertEqual(len(cps), 2)
        # Ordered by -check_date (most recent first)
        self.assertGreaterEqual(cps[0].check_date, cps[1].check_date)


# ---------------------------------------------------------------------------
# C. Verify Plan Tests
# ---------------------------------------------------------------------------

class VerifyPlanTest(TestCase):
    """Test verify_plan service function."""

    def setUp(self):
        self.sub = _create_subscriber(
            subscription_number="01-500003-01",
            phone_number="+962795000003",
        )
        _seed_readings(self.sub, days=14)
        self.plan = _create_plan(self.sub)

    def test_verify_plan_updates_status(self):
        from plans.services import verify_plan
        verify_plan(self.plan)
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.status, "verified")

    def test_verify_plan_stores_verification_result(self):
        from plans.services import verify_plan
        verify_plan(self.plan)
        self.plan.refresh_from_db()
        self.assertIsNotNone(self.plan.verification_result)
        self.assertIn("verified_at", self.plan.verification_result)
        self.assertIn("baseline_daily_kwh", self.plan.verification_result)
        self.assertIn("final_daily_kwh", self.plan.verification_result)
        self.assertIn("change_percent", self.plan.verification_result)
        self.assertIn("improved", self.plan.verification_result)

    def test_verify_plan_returns_progress(self):
        from plans.services import verify_plan
        result = verify_plan(self.plan)
        self.assertIn("plan_id", result)
        self.assertIn("change_percent", result)

    def test_verify_plan_creates_checkpoint(self):
        from plans.services import verify_plan
        verify_plan(self.plan)
        self.assertEqual(PlanCheckpoint.objects.filter(plan=self.plan).count(), 1)


# ---------------------------------------------------------------------------
# D. RAG Retriever Fallback Tests
# ---------------------------------------------------------------------------

class RAGRetrieverFallbackTest(TestCase):
    """Test rag/retriever.py keyword fallback and ChromaDB mock path."""

    def test_keyword_search_returns_results(self):
        from rag.retriever import _search_keywords
        results = _search_keywords("tariff rates price", 3)
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)

    def test_keyword_search_result_format(self):
        from rag.retriever import _search_keywords
        results = _search_keywords("water heater tips", 3)
        for r in results:
            self.assertIn("title", r)
            self.assertIn("content", r)
            self.assertIn("source", r)

    def test_keyword_search_relevance(self):
        from rag.retriever import _search_keywords
        results = _search_keywords("tariff tier rate fils", 3)
        titles = [r["title"] for r in results]
        self.assertTrue(
            any("Tariff" in t for t in titles),
            f"Expected tariff result, got: {titles}"
        )

    def test_keyword_search_arabic(self):
        from rag.retriever import _search_keywords
        results = _search_keywords("تعرفة سعر شريحة", 3)
        self.assertGreater(len(results), 0)

    def test_keyword_search_no_match_returns_defaults(self):
        from rag.retriever import _search_keywords
        results = _search_keywords("xyznonexistent123", 3)
        self.assertEqual(len(results), 3)

    def test_keyword_search_respects_n_results(self):
        from rag.retriever import _search_keywords
        results = _search_keywords("electricity", 1)
        self.assertEqual(len(results), 1)

    def test_search_uses_keyword_fallback_by_default(self):
        """Without chromadb installed, search() should use keyword fallback."""
        import rag.retriever as ret
        # Reset state so _try_init_chroma runs fresh
        original_attempted = ret._chroma_init_attempted
        original_available = ret._CHROMA_AVAILABLE
        ret._chroma_init_attempted = False
        ret._CHROMA_AVAILABLE = False
        try:
            results = ret.search("tariff", n_results=2)
            self.assertIsInstance(results, list)
            self.assertGreater(len(results), 0)
            # Should still be unavailable since chromadb isn't installed
            self.assertFalse(ret._CHROMA_AVAILABLE)
        finally:
            ret._chroma_init_attempted = original_attempted
            ret._CHROMA_AVAILABLE = original_available

    @patch("rag.retriever._CHROMA_AVAILABLE", True)
    @patch("rag.retriever._model")
    @patch("rag.retriever._collection")
    def test_vector_search_when_available(self, mock_collection, mock_model):
        """When ChromaDB is available, search should use vector path."""
        from rag.retriever import _search_vector

        mock_model.encode.return_value = MagicMock(tolist=lambda: [0.1] * 1024)
        mock_collection.query.return_value = {
            "documents": [["Test document about energy"]],
            "metadatas": [[{"source": "test.md"}]],
        }

        results = _search_vector("energy tips", 3)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["content"], "Test document about energy")
        mock_model.encode.assert_called_once()


# ---------------------------------------------------------------------------
# E. RAG Ingestion Tests
# ---------------------------------------------------------------------------

class RAGIngestTest(TestCase):
    """Test rag/ingest.py chunk_text and ingest_all."""

    def test_chunk_text_short(self):
        from rag.ingest import chunk_text
        text = "This is a short text"
        chunks = chunk_text(text, chunk_size=512)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], text)

    def test_chunk_text_empty(self):
        from rag.ingest import chunk_text
        chunks = chunk_text("")
        self.assertEqual(len(chunks), 0)

    def test_chunk_text_splits_long_text(self):
        from rag.ingest import chunk_text
        words = ["word"] * 100
        text = " ".join(words)
        chunks = chunk_text(text, chunk_size=30, overlap=10)
        self.assertGreater(len(chunks), 1)

    def test_chunk_text_overlap(self):
        from rag.ingest import chunk_text
        words = [f"w{i}" for i in range(60)]
        text = " ".join(words)
        chunks = chunk_text(text, chunk_size=30, overlap=10)
        # First chunk should have words 0-29
        self.assertIn("w0", chunks[0])
        # Second chunk should start from word 20 (step = 30-10 = 20)
        self.assertIn("w20", chunks[1])
        # Overlap: word 20-29 should appear in both chunks
        self.assertIn("w25", chunks[0])
        self.assertIn("w25", chunks[1])

    def test_chunk_text_all_words_covered(self):
        from rag.ingest import chunk_text
        words = [f"w{i}" for i in range(50)]
        text = " ".join(words)
        chunks = chunk_text(text, chunk_size=20, overlap=5)
        all_text = " ".join(chunks)
        for w in words:
            self.assertIn(w, all_text)

    def test_ingest_all_with_mocked_chromadb(self):
        import sys
        from rag.ingest import ingest_all

        mock_chromadb = MagicMock()
        mock_collection = MagicMock()
        mock_chromadb.PersistentClient.return_value.get_or_create_collection.return_value = mock_collection

        mock_st_module = MagicMock()
        mock_model = MagicMock()
        mock_model.encode.return_value = MagicMock(tolist=lambda: [0.1] * 1024)
        mock_st_module.SentenceTransformer.return_value = mock_model

        with patch.dict(sys.modules, {
            "chromadb": mock_chromadb,
            "sentence_transformers": mock_st_module,
        }):
            count = ingest_all()

        self.assertGreater(count, 0)
        mock_collection.upsert.assert_called()


# ---------------------------------------------------------------------------
# F. Notification Tasks Tests
# ---------------------------------------------------------------------------

class NotificationTasksTest(TestCase):
    """Test notification Celery tasks with mocked send_text."""

    def setUp(self):
        self.sub = _create_subscriber(
            subscription_number="01-500004-01",
            phone_number="+962795000004",
            is_verified=True,
            wants_weekly_report=True,
            wants_spike_alerts=True,
        )
        _seed_readings(self.sub, days=30)

    @patch("notifications.tasks.send_text")
    def test_weekly_report_sends_to_opted_in(self, mock_send):
        from notifications.tasks import send_weekly_reports
        mock_send.return_value = "SM123"
        count = send_weekly_reports()
        self.assertEqual(count, 1)
        mock_send.assert_called_once()

    @patch("notifications.tasks.send_text")
    def test_weekly_report_skips_unverified(self, mock_send):
        from notifications.tasks import send_weekly_reports
        self.sub.is_verified = False
        self.sub.save()
        count = send_weekly_reports()
        self.assertEqual(count, 0)
        mock_send.assert_not_called()

    @patch("notifications.tasks.send_text")
    def test_weekly_report_skips_opted_out(self, mock_send):
        from notifications.tasks import send_weekly_reports
        self.sub.wants_weekly_report = False
        self.sub.save()
        count = send_weekly_reports()
        self.assertEqual(count, 0)
        mock_send.assert_not_called()

    @patch("notifications.tasks.send_text")
    def test_weekly_report_arabic(self, mock_send):
        from notifications.tasks import send_weekly_reports
        self.sub.language = "ar"
        self.sub.save()
        mock_send.return_value = "SM123"
        send_weekly_reports()
        call_args = mock_send.call_args
        message = call_args[0][1]
        self.assertIn("التقرير الأسبوعي", message)

    @patch("notifications.tasks.send_text")
    def test_weekly_report_english(self, mock_send):
        from notifications.tasks import send_weekly_reports
        mock_send.return_value = "SM123"
        send_weekly_reports()
        call_args = mock_send.call_args
        message = call_args[0][1]
        self.assertIn("Weekly Consumption Report", message)

    @patch("notifications.tasks.send_text")
    def test_spike_alert_no_spikes(self, mock_send):
        """If no spikes detected, no alert should be sent."""
        from notifications.tasks import check_spike_alerts
        # With normal data, we may or may not have spikes.
        # The function should at least not crash.
        check_spike_alerts()
        # Just verify it ran without error

    @patch("meter.analyzer.MeterAnalyzer.detect_spikes")
    @patch("notifications.tasks.send_text")
    def test_spike_alert_sends_when_spike_found(self, mock_send, mock_detect):
        from notifications.tasks import check_spike_alerts
        mock_detect.return_value = [
            {
                "timestamp": "2026-02-09T19:00:00+03:00",
                "power_kw": 8.5,
                "baseline_kw": 2.0,
                "spike_factor": 4.25,
                "tou_period": "peak",
                "duration_minutes": 30,
                "estimated_extra_cost_fils": 650,
            }
        ]
        mock_send.return_value = "SM123"
        count = check_spike_alerts()
        self.assertEqual(count, 1)
        mock_send.assert_called_once()
        message = mock_send.call_args[0][1]
        self.assertIn("8.5", message)

    @patch("notifications.tasks.send_text")
    def test_spike_alert_skips_opted_out(self, mock_send):
        from notifications.tasks import check_spike_alerts
        self.sub.wants_spike_alerts = False
        self.sub.save()
        check_spike_alerts()
        mock_send.assert_not_called()

    @patch("notifications.tasks.send_text")
    @patch("notifications.tasks.check_progress")
    def test_plan_verification_sends_notification(self, mock_progress, mock_send):
        from notifications.tasks import check_plan_verifications
        plan = _create_plan(self.sub)
        plan.verify_after_date = timezone.now().date() - timedelta(days=1)
        plan.save()

        mock_progress.return_value = {
            "plan_id": plan.id,
            "plan_summary": plan.plan_summary,
            "status": "active",
            "baseline_daily_kwh": 25.0,
            "current_daily_kwh": 20.0,
            "change_percent": -20.0,
            "on_track": True,
            "is_improving": True,
            "ready_for_verification": True,
            "estimated_monthly_savings_fils": 5000,
            "estimated_monthly_savings_jod": 5.0,
            "days_monitored": 7,
            "verify_after_date": str(plan.verify_after_date),
        }
        mock_send.return_value = "SM123"

        count = check_plan_verifications()
        self.assertEqual(count, 1)
        mock_send.assert_called_once()

    @patch("notifications.tasks.send_text")
    @patch("notifications.tasks.check_progress")
    def test_plan_verification_updates_plan_status(self, mock_progress, mock_send):
        from notifications.tasks import check_plan_verifications
        plan = _create_plan(self.sub)
        plan.verify_after_date = timezone.now().date() - timedelta(days=1)
        plan.save()

        mock_progress.return_value = {
            "plan_id": plan.id,
            "plan_summary": plan.plan_summary,
            "status": "active",
            "baseline_daily_kwh": 25.0,
            "current_daily_kwh": 20.0,
            "change_percent": -20.0,
            "on_track": True,
            "is_improving": True,
            "ready_for_verification": True,
            "estimated_monthly_savings_fils": 5000,
            "estimated_monthly_savings_jod": 5.0,
            "days_monitored": 7,
            "verify_after_date": str(plan.verify_after_date),
        }
        mock_send.return_value = "SM123"

        check_plan_verifications()
        plan.refresh_from_db()
        self.assertEqual(plan.status, "verified")

    @patch("notifications.tasks.send_text")
    def test_plan_verification_skips_future_plans(self, mock_send):
        from notifications.tasks import check_plan_verifications
        plan = _create_plan(self.sub)
        plan.verify_after_date = timezone.now().date() + timedelta(days=30)
        plan.save()

        count = check_plan_verifications()
        self.assertEqual(count, 0)
        mock_send.assert_not_called()


# ---------------------------------------------------------------------------
# G. Celery Beat Schedule Tests
# ---------------------------------------------------------------------------

class CeleryBeatScheduleTest(TestCase):
    """Test CELERY_BEAT_SCHEDULE in settings."""

    def test_schedule_has_weekly_reports(self):
        from django.conf import settings
        self.assertIn("weekly-reports", settings.CELERY_BEAT_SCHEDULE)
        task = settings.CELERY_BEAT_SCHEDULE["weekly-reports"]
        self.assertEqual(task["task"], "notifications.tasks.send_weekly_reports")

    def test_schedule_has_spike_alerts(self):
        from django.conf import settings
        self.assertIn("spike-alerts", settings.CELERY_BEAT_SCHEDULE)
        task = settings.CELERY_BEAT_SCHEDULE["spike-alerts"]
        self.assertEqual(task["task"], "notifications.tasks.check_spike_alerts")

    def test_schedule_has_plan_verifications(self):
        from django.conf import settings
        self.assertIn("plan-verifications", settings.CELERY_BEAT_SCHEDULE)
        task = settings.CELERY_BEAT_SCHEDULE["plan-verifications"]
        self.assertEqual(task["task"], "notifications.tasks.check_plan_verifications")


# ---------------------------------------------------------------------------
# H. Ingest Management Command Tests
# ---------------------------------------------------------------------------

class IngestManagementCommandTest(TestCase):
    """Test the ingest_knowledge management command."""

    @patch("rag.ingest.ingest_all", return_value=42)
    def test_command_calls_ingest_all(self, mock_ingest):
        from django.core.management import call_command
        from io import StringIO
        out = StringIO()
        call_command("ingest_knowledge", stdout=out)
        mock_ingest.assert_called_once()
        self.assertIn("42", out.getvalue())

    @patch("rag.ingest.ingest_all", side_effect=ImportError("chromadb not installed"))
    def test_command_handles_import_error(self, mock_ingest):
        from django.core.management import call_command
        from io import StringIO
        err = StringIO()
        call_command("ingest_knowledge", stderr=err)
        output = err.getvalue()
        self.assertIn("chromadb", output.lower())

    @patch("rag.ingest.ingest_all", side_effect=RuntimeError("disk full"))
    def test_command_handles_generic_error(self, mock_ingest):
        from django.core.management import call_command
        from io import StringIO
        err = StringIO()
        call_command("ingest_knowledge", stderr=err)
        self.assertIn("disk full", err.getvalue())


# ---------------------------------------------------------------------------
# I. Delete Plan Tests
# ---------------------------------------------------------------------------

class DeletePlanTest(TestCase):
    """Test delete_plan service function."""

    def setUp(self):
        self.sub = _create_subscriber(
            subscription_number="01-500010-01",
            phone_number="+962795000010",
        )
        _seed_readings(self.sub, days=14)
        self.plan = _create_plan(self.sub)

    @patch("plans.services.send_text")
    def test_delete_active_plan(self, mock_send):
        from plans.services import delete_plan
        plan_id = self.plan.id
        result = delete_plan(self.sub, plan_id)
        self.assertEqual(result["status"], "deleted")
        self.assertFalse(OptimizationPlan.objects.filter(id=plan_id).exists())

    @patch("plans.services.send_text")
    def test_delete_sends_whatsapp(self, mock_send):
        from plans.services import delete_plan
        mock_send.return_value = "SM123"
        summary = self.plan.plan_summary
        delete_plan(self.sub, self.plan.id)
        mock_send.assert_called_once()
        message = mock_send.call_args[0][1]
        self.assertIn(summary[:50], message)

    @patch("plans.services.send_text")
    def test_delete_nonexistent_plan(self, mock_send):
        from plans.services import delete_plan
        result = delete_plan(self.sub, 99999)
        self.assertIn("error", result)

    @patch("plans.services.send_text")
    def test_delete_defaults_to_active_plan(self, mock_send):
        from plans.services import delete_plan
        plan_id = self.plan.id
        result = delete_plan(self.sub)
        self.assertEqual(result["plan_id"], plan_id)
        self.assertEqual(result["status"], "deleted")
        self.assertFalse(OptimizationPlan.objects.filter(id=plan_id).exists())

    @patch("plans.services.send_text")
    def test_delete_no_active_plan(self, mock_send):
        from plans.services import delete_plan
        self.plan.status = "completed"
        self.plan.save()
        result = delete_plan(self.sub)
        self.assertIn("error", result)

    @patch("plans.services.send_text")
    def test_delete_arabic_notification(self, mock_send):
        from plans.services import delete_plan
        self.sub.language = "ar"
        self.sub.save()
        mock_send.return_value = "SM123"
        delete_plan(self.sub, self.plan.id)
        message = mock_send.call_args[0][1]
        self.assertIn("تم إلغاء الخطة", message)

    @patch("plans.services.send_text")
    def test_delete_also_removes_checkpoints(self, mock_send):
        from plans.services import delete_plan, check_progress
        check_progress(self.sub, self.plan.id)
        self.assertEqual(PlanCheckpoint.objects.filter(plan=self.plan).count(), 1)
        delete_plan(self.sub, self.plan.id)
        self.assertEqual(PlanCheckpoint.objects.filter(plan_id=self.plan.id).count(), 0)


# ---------------------------------------------------------------------------
# J. Delete Plan Agent Tool Test
# ---------------------------------------------------------------------------

class DeletePlanToolTest(TestCase):
    """Test delete_plan tool execution via agent tools."""

    def setUp(self):
        self.sub = _create_subscriber(
            subscription_number="01-500011-01",
            phone_number="+962795000011",
        )
        _seed_readings(self.sub, days=14)
        self.plan = _create_plan(self.sub)

    @patch("plans.services.send_text")
    def test_execute_delete_plan_tool(self, mock_send):
        import json
        from agent.tools import execute_tool
        result = json.loads(execute_tool("delete_plan", {
            "phone": self.sub.phone_number,
            "plan_id": self.plan.id,
        }))
        self.assertEqual(result["status"], "deleted")

    @patch("plans.services.send_text")
    def test_execute_delete_plan_tool_no_plan_id(self, mock_send):
        import json
        from agent.tools import execute_tool
        result = json.loads(execute_tool("delete_plan", {
            "phone": self.sub.phone_number,
        }))
        self.assertEqual(result["status"], "deleted")
        self.assertEqual(result["plan_id"], self.plan.id)


# ---------------------------------------------------------------------------
# K. Plan Deleted Template Tests
# ---------------------------------------------------------------------------

class PlanDeletedTemplateTest(TestCase):
    """Test plan deleted message templates."""

    def test_deleted_en_formats(self):
        from notifications.message_templates import PLAN_ABANDONED_EN
        msg = PLAN_ABANDONED_EN.format(plan_summary="Shift EV charging")
        self.assertIn("Plan Cancelled", msg)
        self.assertIn("Shift EV charging", msg)

    def test_deleted_ar_formats(self):
        from notifications.message_templates import PLAN_ABANDONED_AR
        msg = PLAN_ABANDONED_AR.format(plan_summary="تحويل شحن السيارة")
        self.assertIn("تم إلغاء الخطة", msg)
        self.assertIn("تحويل شحن السيارة", msg)


# ---------------------------------------------------------------------------
# L. Message Templates Tests
# ---------------------------------------------------------------------------

class MessageTemplatesTest(TestCase):
    """Test notification message templates format correctly."""

    def test_weekly_report_ar_formats(self):
        from notifications.message_templates import WEEKLY_REPORT_AR
        msg = WEEKLY_REPORT_AR.format(
            avg_daily_kwh=25.5,
            total_kwh=178.5,
            change_line="test",
        )
        self.assertIn("25.5", msg)
        self.assertIn("178.5", msg)

    def test_weekly_report_en_formats(self):
        from notifications.message_templates import WEEKLY_REPORT_EN
        msg = WEEKLY_REPORT_EN.format(
            avg_daily_kwh=25.5,
            total_kwh=178.5,
            change_line="test",
        )
        self.assertIn("Weekly Consumption Report", msg)

    def test_spike_alert_ar_formats(self):
        from notifications.message_templates import SPIKE_ALERT_AR
        msg = SPIKE_ALERT_AR.format(power_kw=8.5, time="19:00", factor=4.25)
        self.assertIn("8.5", msg)

    def test_plan_result_improved_formats(self):
        from notifications.message_templates import PLAN_RESULT_IMPROVED_EN
        msg = PLAN_RESULT_IMPROVED_EN.format(
            plan_summary="Shift EV charging",
            change_percent=20.0,
            savings_kwh=5.0,
        )
        self.assertIn("20.0", msg)
        self.assertIn("5.0", msg)

    def test_plan_result_not_improved_formats(self):
        from notifications.message_templates import PLAN_RESULT_NOT_IMPROVED_EN
        msg = PLAN_RESULT_NOT_IMPROVED_EN.format(
            plan_summary="Shift EV charging",
            change_percent=5.0,
        )
        self.assertIn("5.0", msg)

"""
Phase 3 — AI Agent Core Tests.
Tests LLM client, intent classifier, conversation manager, tool execution,
plan services, agent chat endpoint, and RAG retriever.

All LLM API calls are mocked — no real API key needed.
"""

import json
from datetime import timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client
from django.utils import timezone

from accounts.models import Subscriber
from meter.models import MeterReading
from meter.generator import generate_meter_data
from plans.models import OptimizationPlan
from tariff.engine import JORDAN_TZ


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_test_subscriber(**kwargs):
    defaults = {
        "subscription_number": "01-300001-01",
        "phone_number": "+962793000001",
        "name": "Test User",
        "area": "Abdoun",
        "tariff_category": "residential",
        "has_ev": True,
        "is_verified": True,
    }
    defaults.update(kwargs)
    return Subscriber.objects.create(**defaults)


def _seed_readings(subscriber, days=7):
    """Generate and save meter readings for testing."""
    readings = generate_meter_data(subscriber, "ev_peak_charger", days=days)
    MeterReading.objects.bulk_create(readings, batch_size=1000)


def _mock_groq_response(text="Hello!", finish_reason="stop", tool_calls=None):
    """Create a mock Groq/OpenAI-style response."""
    msg = MagicMock()
    msg.content = text
    msg.tool_calls = tool_calls

    choice = MagicMock()
    choice.message = msg
    choice.finish_reason = finish_reason

    response = MagicMock()
    response.choices = [choice]
    return response


# ---------------------------------------------------------------------------
# A. LLM Client Tests
# ---------------------------------------------------------------------------

class LLMClientTest(TestCase):
    """Test core/llm_client.py wrapper functions."""

    @patch("core.llm_client._get_client")
    def test_chat_with_tools_calls_api(self, mock_get_client):
        from core.llm_client import chat_with_tools, MAIN_MODEL

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_groq_response()

        chat_with_tools(
            messages=[{"role": "user", "content": "Hi"}],
            system="You are helpful.",
        )
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        self.assertEqual(call_kwargs["model"], MAIN_MODEL)
        self.assertEqual(call_kwargs["max_tokens"], 1024)
        # System prompt should be injected as first message
        self.assertEqual(call_kwargs["messages"][0]["role"], "system")

    @patch("core.llm_client._get_client")
    def test_classify_fast_uses_fast_model(self, mock_get_client):
        from core.llm_client import classify_fast, FAST_MODEL

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_groq_response(
            text='{"intent": "general"}'
        )

        result = classify_fast("Hello", system="Classify")
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        self.assertEqual(call_kwargs["model"], FAST_MODEL)
        self.assertEqual(call_kwargs["max_tokens"], 200)
        self.assertEqual(result, '{"intent": "general"}')

    @patch("core.llm_client._get_client")
    def test_chat_with_tools_passes_tools(self, mock_get_client):
        from core.llm_client import chat_with_tools

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_groq_response()

        tools = [{"type": "function", "function": {"name": "test", "parameters": {}}}]
        chat_with_tools(
            messages=[{"role": "user", "content": "Hi"}],
            system="sys",
            tools=tools,
        )
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        self.assertIn("tools", call_kwargs)
        self.assertEqual(len(call_kwargs["tools"]), 1)
        self.assertEqual(call_kwargs["tool_choice"], "auto")


# ---------------------------------------------------------------------------
# B. Intent Classifier Tests
# ---------------------------------------------------------------------------

class IntentClassifierTest(TestCase):
    """Test agent/intent.py classify_intent function."""

    @patch("agent.intent.classify_fast")
    def test_bill_query_intent(self, mock_classify):
        from agent.intent import classify_intent
        mock_classify.return_value = '{"intent": "bill_query", "confidence": 0.95, "language": "ar"}'
        result = classify_intent("ليش فاتورتي غالية؟")
        self.assertEqual(result["intent"], "bill_query")
        self.assertEqual(result["language"], "ar")

    @patch("agent.intent.classify_fast")
    def test_tariff_question_english(self, mock_classify):
        from agent.intent import classify_intent
        mock_classify.return_value = '{"intent": "tariff_question", "confidence": 0.9, "language": "en"}'
        result = classify_intent("What are the peak hours?")
        self.assertEqual(result["intent"], "tariff_question")
        self.assertEqual(result["language"], "en")

    @patch("agent.intent.classify_fast")
    def test_onboarding_intent(self, mock_classify):
        from agent.intent import classify_intent
        mock_classify.return_value = '{"intent": "onboarding", "confidence": 0.88, "language": "ar"}'
        result = classify_intent("بدي اسجل")
        self.assertEqual(result["intent"], "onboarding")

    @patch("agent.intent.classify_fast")
    def test_unknown_intent_falls_back_to_general(self, mock_classify):
        from agent.intent import classify_intent
        mock_classify.return_value = '{"intent": "unknown_thing", "confidence": 0.5, "language": "ar"}'
        result = classify_intent("something weird")
        self.assertEqual(result["intent"], "general")

    @patch("agent.intent.classify_fast")
    def test_json_parse_error_falls_back(self, mock_classify):
        from agent.intent import classify_intent
        mock_classify.return_value = "not valid json at all"
        result = classify_intent("test")
        self.assertEqual(result["intent"], "general")
        self.assertEqual(result["confidence"], 0.5)

    @patch("agent.intent.classify_fast")
    def test_all_valid_intents(self, mock_classify):
        from agent.intent import classify_intent, INTENTS
        for intent in INTENTS:
            mock_classify.return_value = json.dumps({
                "intent": intent, "confidence": 0.9, "language": "ar"
            })
            result = classify_intent("test")
            self.assertEqual(result["intent"], intent)


# ---------------------------------------------------------------------------
# C. Conversation Manager Tests
# ---------------------------------------------------------------------------

class ConversationManagerTest(TestCase):
    """Test agent/conversation.py ConversationManager."""

    def setUp(self):
        from agent.conversation import ConversationManager
        self.manager = ConversationManager()
        self.phone = "+962799999999"

    def tearDown(self):
        self.manager.clear_state(self.phone)

    def test_default_state_for_new_phone(self):
        state = self.manager.get_state(self.phone)
        self.assertEqual(state["messages"], [])
        self.assertEqual(state["language"], "ar")
        self.assertIsNone(state["last_intent"])

    def test_save_and_get_roundtrip(self):
        state = {
            "messages": [{"role": "user", "content": "hi"}],
            "language": "en",
            "last_intent": "general",
        }
        self.manager.save_state(self.phone, state)
        loaded = self.manager.get_state(self.phone)
        self.assertEqual(loaded["messages"], state["messages"])
        self.assertEqual(loaded["language"], "en")
        self.assertEqual(loaded["last_intent"], "general")

    def test_clear_state(self):
        self.manager.save_state(self.phone, {"messages": [{"role": "user", "content": "x"}], "language": "ar", "last_intent": None})
        self.manager.clear_state(self.phone)
        state = self.manager.get_state(self.phone)
        self.assertEqual(state["messages"], [])

    def test_messages_list_preserved(self):
        msgs = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi there"},
            {"role": "user", "content": "how are you"},
        ]
        self.manager.save_state(self.phone, {"messages": msgs, "language": "ar", "last_intent": "general"})
        loaded = self.manager.get_state(self.phone)
        self.assertEqual(len(loaded["messages"]), 3)

    def test_arabic_text_preserved(self):
        msgs = [{"role": "user", "content": "مرحبا كيف حالك"}]
        self.manager.save_state(self.phone, {"messages": msgs, "language": "ar", "last_intent": None})
        loaded = self.manager.get_state(self.phone)
        self.assertEqual(loaded["messages"][0]["content"], "مرحبا كيف حالك")


# ---------------------------------------------------------------------------
# D. Tool Execution Tests
# ---------------------------------------------------------------------------

class ToolExecutionTest(TestCase):
    """Test agent/tools.py execute_tool function."""

    def setUp(self):
        self.sub = _create_test_subscriber()
        _seed_readings(self.sub, days=7)

    def test_get_subscriber_info(self):
        from agent.tools import execute_tool
        result = json.loads(execute_tool("get_subscriber_info", {"phone": "+962793000001"}))
        self.assertEqual(result["name"], "Test User")
        self.assertEqual(result["subscription_number"], "01-300001-01")
        self.assertEqual(result["area"], "Abdoun")
        self.assertTrue(result["has_ev"])

    def test_get_consumption_summary(self):
        from agent.tools import execute_tool
        result = json.loads(execute_tool("get_consumption_summary", {"phone": "+962793000001", "days": 7}))
        self.assertIn("total_kwh", result)
        self.assertIn("avg_daily_kwh", result)

    def test_get_daily_detail(self):
        from agent.tools import execute_tool
        day = (timezone.now() - timedelta(days=3)).strftime("%Y-%m-%d")
        result = json.loads(execute_tool("get_daily_detail", {"phone": "+962793000001", "date": day}))
        self.assertIn("total_kwh", result)

    def test_detect_spikes(self):
        from agent.tools import execute_tool
        result = json.loads(execute_tool("detect_spikes", {"phone": "+962793000001"}))
        self.assertIsInstance(result, (list, dict))

    def test_detect_patterns(self):
        from agent.tools import execute_tool
        result = json.loads(execute_tool("detect_patterns", {"phone": "+962793000001"}))
        self.assertIsInstance(result, (list, dict))

    def test_get_bill_forecast(self):
        from agent.tools import execute_tool
        result = json.loads(execute_tool("get_bill_forecast", {"phone": "+962793000001"}))
        self.assertIsInstance(result, dict)

    def test_calculate_bill(self):
        from agent.tools import execute_tool
        result = json.loads(execute_tool("calculate_bill", {"monthly_kwh": 500}))
        self.assertIn("total_fils", result)
        self.assertIn("total_jod", result)
        self.assertIn("tier_breakdown", result)

    def test_get_tou_period(self):
        from agent.tools import execute_tool
        result = json.loads(execute_tool("get_tou_period", {}))
        self.assertIn("period", result)
        self.assertIn(result["period"], ["off_peak", "partial_peak", "peak"])

    def test_search_knowledge(self):
        from agent.tools import execute_tool
        result = json.loads(execute_tool("search_knowledge", {"query": "tariff rates"}))
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        self.assertIn("title", result[0])
        self.assertIn("content", result[0])

    def test_unknown_tool(self):
        from agent.tools import execute_tool
        result = json.loads(execute_tool("nonexistent_tool", {}))
        self.assertIn("error", result)

    def test_subscriber_not_found(self):
        from agent.tools import execute_tool
        result = json.loads(execute_tool("get_subscriber_info", {"phone": "+962799999999"}))
        self.assertIn("error", result)
        self.assertIn("not found", result["error"].lower())


# ---------------------------------------------------------------------------
# E. Plan Services Tests
# ---------------------------------------------------------------------------

class PlanServicesTest(TestCase):
    """Test plans/services.py functions."""

    def setUp(self):
        self.sub = _create_test_subscriber(
            subscription_number="01-400001-01",
            phone_number="+962794000001",
            name="Plan Test User",
        )
        _seed_readings(self.sub, days=14)

    def test_create_optimization_plan(self):
        from plans.services import create_optimization_plan
        plan = create_optimization_plan(self.sub, {
            "detected_pattern": "High consumption 7PM-11PM weekdays",
            "user_hypothesis": "EV charging at peak",
            "plan_summary": "Shift EV charging to off-peak",
            "actions": [
                {
                    "action": "Schedule EV charging 1AM-5AM",
                    "expected_impact_kwh": 5.0,
                    "expected_savings_fils_per_day": 1456,
                }
            ],
            "monitoring_days": 7,
        })
        self.assertIsNotNone(plan.id)
        self.assertEqual(plan.status, "active")
        self.assertEqual(plan.subscriber, self.sub)
        self.assertGreater(plan.baseline_daily_kwh, 0)

    def test_get_active_plan_returns_plan(self):
        from plans.services import create_optimization_plan, get_active_plan
        create_optimization_plan(self.sub, {
            "detected_pattern": "test",
            "user_hypothesis": "test",
            "plan_summary": "test plan",
            "actions": [],
        })
        plan = get_active_plan(self.sub)
        self.assertIsNotNone(plan)
        self.assertEqual(plan.plan_summary, "test plan")

    def test_get_active_plan_returns_none(self):
        from plans.services import get_active_plan
        plan = get_active_plan(self.sub)
        self.assertIsNone(plan)

    def test_check_progress(self):
        from plans.services import create_optimization_plan, check_progress
        plan = create_optimization_plan(self.sub, {
            "detected_pattern": "test",
            "user_hypothesis": "test",
            "plan_summary": "test plan",
            "actions": [],
        })
        result = check_progress(self.sub, plan.id)
        self.assertIn("baseline_daily_kwh", result)
        self.assertIn("current_daily_kwh", result)
        self.assertIn("change_percent", result)
        self.assertIn("on_track", result)

    def test_plan_tools_via_execute_tool(self):
        from agent.tools import execute_tool
        # Create plan
        result = json.loads(execute_tool("create_plan", {
            "phone": "+962794000001",
            "detected_pattern": "High peak usage",
            "user_hypothesis": "EV charging",
            "plan_summary": "Shift EV to off-peak",
            "actions": [{"action": "Use timer", "expected_impact_kwh": 3, "expected_savings_fils_per_day": 800}],
            "monitoring_days": 7,
        }))
        self.assertIn("plan_id", result)
        plan_id = result["plan_id"]

        # Get active plan
        result2 = json.loads(execute_tool("get_active_plan", {"phone": "+962794000001"}))
        self.assertEqual(result2["plan_id"], plan_id)

        # Check progress
        result3 = json.loads(execute_tool("check_plan_progress", {"phone": "+962794000001", "plan_id": plan_id}))
        self.assertIn("change_percent", result3)


# ---------------------------------------------------------------------------
# F. Agent Chat Endpoint Tests
# ---------------------------------------------------------------------------

class AgentChatEndpointTest(TestCase):
    """Test POST /api/agent/chat/ endpoint."""

    def setUp(self):
        self.client = Client()
        self.sub = _create_test_subscriber(
            subscription_number="01-500001-01",
            phone_number="+962795000001",
            name="Chat Test User",
        )

    @patch("agent.coach.chat_with_tools")
    @patch("agent.coach.classify_intent")
    def test_valid_message_returns_200(self, mock_classify, mock_chat):
        mock_classify.return_value = {"intent": "general", "confidence": 0.9, "language": "ar"}
        mock_chat.return_value = _mock_groq_response(text="مرحبا! كيف بقدر أساعدك؟")
        response = self.client.post(
            "/api/agent/chat/",
            data=json.dumps({"phone": "+962795000001", "message": "مرحبا"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("reply", data)
        self.assertIn("phone", data)
        self.assertEqual(data["phone"], "+962795000001")

    def test_missing_phone_returns_400(self):
        response = self.client.post(
            "/api/agent/chat/",
            data=json.dumps({"message": "hello"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_missing_message_returns_400(self):
        response = self.client.post(
            "/api/agent/chat/",
            data=json.dumps({"phone": "+962795000001"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    @patch("agent.coach.chat_with_tools")
    @patch("agent.coach.classify_intent")
    def test_response_has_reply_field(self, mock_classify, mock_chat):
        mock_classify.return_value = {"intent": "general", "confidence": 0.9, "language": "ar"}
        mock_chat.return_value = _mock_groq_response(text="Hello!")
        response = self.client.post(
            "/api/agent/chat/",
            data=json.dumps({"phone": "+962795000001", "message": "hi"}),
            content_type="application/json",
        )
        data = response.json()
        self.assertEqual(data["reply"], "Hello!")


# ---------------------------------------------------------------------------
# G. RAG Retriever Tests
# ---------------------------------------------------------------------------

class RAGRetrieverTest(TestCase):
    """Test rag/retriever.py search function."""

    def test_search_returns_list(self):
        from rag.retriever import search
        results = search("tariff rates")
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)

    def test_results_have_required_fields(self):
        from rag.retriever import search
        results = search("water heater tips")
        for r in results:
            self.assertIn("title", r)
            self.assertIn("content", r)
            self.assertIn("source", r)

    def test_respects_n_results(self):
        from rag.retriever import search
        results = search("electricity", n_results=2)
        self.assertLessEqual(len(results), 2)

    def test_no_match_returns_defaults(self):
        from rag.retriever import search
        results = search("xyznonexistent123")
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)


# ---------------------------------------------------------------------------
# H. Tool Definitions Tests (OpenAI-compatible format)
# ---------------------------------------------------------------------------

class ToolDefinitionsTest(TestCase):
    """Test that TOOLS list has correct OpenAI-compatible structure."""

    def test_tools_count(self):
        from agent.tools import TOOLS
        self.assertEqual(len(TOOLS), 13)

    def test_all_tools_have_openai_format(self):
        from agent.tools import TOOLS
        for tool in TOOLS:
            self.assertEqual(tool["type"], "function")
            self.assertIn("function", tool)
            func = tool["function"]
            self.assertIn("name", func)
            self.assertIn("description", func)
            self.assertIn("parameters", func)
            self.assertEqual(func["parameters"]["type"], "object")

    def test_tool_names_are_unique(self):
        from agent.tools import TOOLS
        names = [t["function"]["name"] for t in TOOLS]
        self.assertEqual(len(names), len(set(names)))

"""
Feature 1 — Persistent Conversation Storage Tests.

Tests ConversationSession/Turn models, DB fallback on cache miss,
save_turn persistence, session expiration, and dashboard API endpoints.
"""

from datetime import timedelta

from django.core.cache import cache
from django.test import TestCase

from accounts.models import Subscriber
from agent.models import ConversationSession, ConversationTurn
from agent.conversation import ConversationManager
from core.clock import now as clock_now


def _create_subscriber(**kwargs):
    defaults = {
        "subscription_number": "01-700001-01",
        "phone_number": "+962797000001",
        "name": "Conv Test User",
        "area": "Sweifieh",
        "tariff_category": "residential",
        "is_verified": True,
        "language": "en",
    }
    defaults.update(kwargs)
    return Subscriber.objects.create(**defaults)


class ConversationSessionModelTest(TestCase):
    """Test ConversationSession and ConversationTurn models."""

    def setUp(self):
        self.sub = _create_subscriber()

    def test_create_session(self):
        session = ConversationSession.objects.create(
            subscriber=self.sub, language="en", last_intent="consumption_check",
        )
        self.assertTrue(session.is_active)
        self.assertIsNone(session.ended_at)
        self.assertEqual(str(session), f"Session {session.id} — {self.sub} (active)")

    def test_create_turn(self):
        session = ConversationSession.objects.create(subscriber=self.sub)
        turn = ConversationTurn.objects.create(
            session=session,
            user_message="How much did I use?",
            agent_response="You used 15 kWh today.",
            intent="consumption_check",
            tools_called=["get_consumption_summary"],
            language="en",
        )
        self.assertEqual(turn.session, session)
        self.assertEqual(turn.tools_called, ["get_consumption_summary"])

    def test_session_turns_ordering(self):
        session = ConversationSession.objects.create(subscriber=self.sub)
        t1 = ConversationTurn.objects.create(
            session=session, user_message="Hi", agent_response="Hello",
        )
        t2 = ConversationTurn.objects.create(
            session=session, user_message="Usage?", agent_response="15 kWh",
        )
        turns = list(session.turns.all())
        self.assertEqual(turns[0].id, t1.id)
        self.assertEqual(turns[1].id, t2.id)


class ConversationManagerDBFallbackTest(TestCase):
    """Test that get_state falls back to DB when cache is empty."""

    def setUp(self):
        self.sub = _create_subscriber()
        self.manager = ConversationManager()
        cache.clear()

    def test_get_state_empty_cache_no_db(self):
        state = self.manager.get_state(self.sub.phone_number)
        self.assertEqual(state["messages"], [])
        self.assertEqual(state["language"], "ar")

    def test_get_state_falls_back_to_db(self):
        session = ConversationSession.objects.create(
            subscriber=self.sub, language="en", last_intent="greeting",
        )
        ConversationTurn.objects.create(
            session=session,
            user_message="Hello",
            agent_response="Hi there!",
            intent="greeting",
            language="en",
        )
        ConversationTurn.objects.create(
            session=session,
            user_message="My usage?",
            agent_response="You used 15 kWh",
            intent="consumption_check",
            language="en",
        )

        state = self.manager.get_state(self.sub.phone_number)
        self.assertEqual(len(state["messages"]), 4)  # 2 turns x 2 messages each
        self.assertEqual(state["language"], "en")
        self.assertEqual(state["messages"][0]["role"], "user")
        self.assertEqual(state["messages"][0]["content"], "Hello")

    def test_expired_session_returns_fresh_state(self):
        session = ConversationSession.objects.create(
            subscriber=self.sub, language="en",
        )
        turn = ConversationTurn.objects.create(
            session=session,
            user_message="Hello",
            agent_response="Hi",
        )
        # Make the turn appear old
        old_time = clock_now() - timedelta(seconds=3600)
        ConversationTurn.objects.filter(id=turn.id).update(created_at=old_time)

        state = self.manager.get_state(self.sub.phone_number)
        self.assertEqual(state["messages"], [])

        session.refresh_from_db()
        self.assertFalse(session.is_active)

    def test_cache_hit_skips_db(self):
        self.manager.save_state(self.sub.phone_number, {
            "messages": [{"role": "user", "content": "cached"}],
            "language": "en",
            "last_intent": "test",
        })
        state = self.manager.get_state(self.sub.phone_number)
        self.assertEqual(state["messages"][0]["content"], "cached")

    def test_reconstructed_state_warms_cache(self):
        session = ConversationSession.objects.create(
            subscriber=self.sub, language="ar",
        )
        ConversationTurn.objects.create(
            session=session,
            user_message="مرحبا",
            agent_response="أهلاً",
        )
        # First call loads from DB
        self.manager.get_state(self.sub.phone_number)
        # Second call should hit cache
        cached = cache.get(f"conv:{self.sub.phone_number}")
        self.assertIsNotNone(cached)


class SaveTurnTest(TestCase):
    """Test save_turn creates sessions and turns in DB."""

    def setUp(self):
        self.sub = _create_subscriber()
        self.manager = ConversationManager()

    def test_save_turn_creates_session_and_turn(self):
        self.manager.save_turn(
            phone=self.sub.phone_number,
            user_message="Hello",
            agent_response="Hi!",
            intent="greeting",
            tools_called=[],
            language="en",
            state={},
        )
        self.assertEqual(ConversationSession.objects.count(), 1)
        self.assertEqual(ConversationTurn.objects.count(), 1)

        session = ConversationSession.objects.first()
        self.assertTrue(session.is_active)
        self.assertEqual(session.language, "en")

        turn = ConversationTurn.objects.first()
        self.assertEqual(turn.user_message, "Hello")
        self.assertEqual(turn.agent_response, "Hi!")

    def test_save_turn_reuses_active_session(self):
        self.manager.save_turn(
            self.sub.phone_number, "Msg 1", "Reply 1", "greeting", [], "en", {},
        )
        self.manager.save_turn(
            self.sub.phone_number, "Msg 2", "Reply 2", "consumption_check",
            ["get_consumption_summary"], "en", {},
        )
        self.assertEqual(ConversationSession.objects.count(), 1)
        self.assertEqual(ConversationTurn.objects.count(), 2)

    def test_save_turn_creates_new_session_after_expiry(self):
        self.manager.save_turn(
            self.sub.phone_number, "Msg 1", "Reply 1", "greeting", [], "en", {},
        )
        # Age the turn
        old_time = clock_now() - timedelta(seconds=3600)
        ConversationTurn.objects.all().update(created_at=old_time)

        self.manager.save_turn(
            self.sub.phone_number, "Msg 2", "Reply 2", "greeting", [], "en", {},
        )
        self.assertEqual(ConversationSession.objects.count(), 2)
        self.assertEqual(ConversationSession.objects.filter(is_active=True).count(), 1)

    def test_save_turn_unknown_phone_is_noop(self):
        self.manager.save_turn(
            "+962790000000", "Hello", "Hi", "greeting", [], "en", {},
        )
        self.assertEqual(ConversationSession.objects.count(), 0)

    def test_save_turn_records_tools_called(self):
        self.manager.save_turn(
            self.sub.phone_number, "My bill?", "Your bill is 30 JOD",
            "consumption_check", ["get_consumption_summary", "get_bill_forecast"],
            "en", {},
        )
        turn = ConversationTurn.objects.first()
        self.assertEqual(turn.tools_called, ["get_consumption_summary", "get_bill_forecast"])


class ConversationDashboardAPITest(TestCase):
    """Test conversation dashboard API endpoints."""

    def setUp(self):
        self.sub = _create_subscriber()
        self.session = ConversationSession.objects.create(
            subscriber=self.sub, language="en", last_intent="greeting",
        )
        self.turn = ConversationTurn.objects.create(
            session=self.session,
            user_message="Hello",
            agent_response="Hi!",
            intent="greeting",
            tools_called=[],
            language="en",
        )

    def test_list_conversations(self):
        resp = self.client.get(f"/api/agent/conversations/{self.sub.subscription_number}/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["session_id"], self.session.id)
        self.assertEqual(data[0]["turn_count"], 1)

    def test_conversation_detail(self):
        resp = self.client.get(
            f"/api/agent/conversations/{self.sub.subscription_number}/{self.session.id}/"
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["session_id"], self.session.id)
        self.assertEqual(len(data["turns"]), 1)
        self.assertEqual(data["turns"][0]["user_message"], "Hello")

    def test_conversation_detail_404(self):
        resp = self.client.get(
            f"/api/agent/conversations/{self.sub.subscription_number}/99999/"
        )
        self.assertEqual(resp.status_code, 404)

    def test_list_conversations_invalid_sub(self):
        resp = self.client.get("/api/agent/conversations/99-999999-99/")
        self.assertEqual(resp.status_code, 404)

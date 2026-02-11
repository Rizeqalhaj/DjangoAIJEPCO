"""
Phase 6 — Polish & Demo Tests.

Tests rate limiting, agent error handling, language detection,
language-aware registration, demo command, and message templates.

All LLM API calls and WhatsApp sends are mocked.
"""

import json
from io import StringIO
from unittest.mock import patch, MagicMock

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase

from accounts.models import Subscriber
from meter.models import MeterReading
from whatsapp.tasks import (
    _process_message_logic,
    _handle_registration,
    _send_split_text,
)
from whatsapp.message_templates import (
    ONBOARDING_AR, ONBOARDING_EN,
    REGISTRATION_SUCCESS_AR, REGISTRATION_SUCCESS_EN,
    WELCOME_BACK_AR, WELCOME_BACK_EN,
    FALLBACK_AR, FALLBACK_EN,
    RATE_LIMIT_AR, RATE_LIMIT_EN,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
# A. Rate Limiter Tests
# ---------------------------------------------------------------------------

class RateLimiterTest(TestCase):
    """Test whatsapp/rate_limiter.py."""

    def setUp(self):
        cache.clear()

    def test_first_message_allowed(self):
        from whatsapp.rate_limiter import check_rate_limit
        self.assertTrue(check_rate_limit("+962790000001"))

    def test_30_messages_allowed(self):
        from whatsapp.rate_limiter import check_rate_limit
        for _ in range(30):
            result = check_rate_limit("+962790000002")
        self.assertTrue(result)

    def test_31st_message_blocked(self):
        from whatsapp.rate_limiter import check_rate_limit
        for _ in range(30):
            check_rate_limit("+962790000003")
        self.assertFalse(check_rate_limit("+962790000003"))

    def test_different_phones_independent(self):
        from whatsapp.rate_limiter import check_rate_limit
        for _ in range(30):
            check_rate_limit("+962790000004")
        # Phone 4 is blocked
        self.assertFalse(check_rate_limit("+962790000004"))
        # Phone 5 is fine
        self.assertTrue(check_rate_limit("+962790000005"))

    def test_cache_cleared_resets_count(self):
        from whatsapp.rate_limiter import check_rate_limit
        for _ in range(30):
            check_rate_limit("+962790000006")
        self.assertFalse(check_rate_limit("+962790000006"))
        cache.clear()
        self.assertTrue(check_rate_limit("+962790000006"))

    def test_rate_limit_key_format(self):
        from whatsapp.rate_limiter import check_rate_limit
        check_rate_limit("+962790000007")
        value = cache.get("rate:+962790000007")
        self.assertEqual(value, 1)

    def test_second_message_increments(self):
        from whatsapp.rate_limiter import check_rate_limit
        check_rate_limit("+962790000008")
        check_rate_limit("+962790000008")
        value = cache.get("rate:+962790000008")
        self.assertEqual(value, 2)


# ---------------------------------------------------------------------------
# B. Rate Limit Integration Tests
# ---------------------------------------------------------------------------

class RateLimitIntegrationTest(TestCase):
    """Test rate limiting integrated into message processing."""

    def setUp(self):
        cache.clear()

    @patch("whatsapp.tasks.send_text")
    def test_rate_limited_arabic_user_gets_ar_message(self, mock_send):
        for _ in range(30):
            cache.incr("rate:+962796000001") if cache.get("rate:+962796000001") else cache.set("rate:+962796000001", 1, 3600)
        cache.set("rate:+962796000001", 31, 3600)
        _process_message_logic("+962796000001", "مرحبا")
        mock_send.assert_called_once_with("+962796000001", RATE_LIMIT_AR)

    @patch("whatsapp.tasks.send_text")
    def test_rate_limited_english_user_gets_en_message(self, mock_send):
        cache.set("rate:+962796000002", 31, 3600)
        _process_message_logic("+962796000002", "Hello")
        mock_send.assert_called_once_with("+962796000002", RATE_LIMIT_EN)

    @patch("whatsapp.tasks.send_text")
    @patch("agent.coach.EnergyDetective.handle_message")
    def test_normal_flow_allowed(self, mock_agent, mock_send):
        Subscriber.objects.create(
            subscription_number="01-600001-01",
            phone_number="+962796000003",
        )
        mock_agent.return_value = "Test response"
        _process_message_logic("+962796000003", "مرحبا")
        mock_agent.assert_called_once()

    @patch("whatsapp.tasks.send_text")
    @patch("agent.coach.EnergyDetective.handle_message")
    def test_rate_limit_blocks_before_agent(self, mock_agent, mock_send):
        Subscriber.objects.create(
            subscription_number="01-600002-01",
            phone_number="+962796000004",
        )
        cache.set("rate:+962796000004", 31, 3600)
        _process_message_logic("+962796000004", "مرحبا")
        mock_agent.assert_not_called()


# ---------------------------------------------------------------------------
# C. Language Detection Tests
# ---------------------------------------------------------------------------

class LanguageDetectionTest(TestCase):
    """Test whatsapp/language_detect.py."""

    def test_arabic_text(self):
        from whatsapp.language_detect import detect_language
        self.assertEqual(detect_language("مرحبا كيف حالك"), "ar")

    def test_english_text(self):
        from whatsapp.language_detect import detect_language
        self.assertEqual(detect_language("Hello how are you"), "en")

    def test_mixed_arabic_majority(self):
        from whatsapp.language_detect import detect_language
        self.assertEqual(detect_language("مرحبا hello مرحبا"), "ar")

    def test_mixed_english_majority(self):
        from whatsapp.language_detect import detect_language
        self.assertEqual(detect_language("Hello there مرحبا buddy"), "en")

    def test_empty_defaults_to_arabic(self):
        from whatsapp.language_detect import detect_language
        self.assertEqual(detect_language(""), "ar")

    def test_whitespace_defaults_to_arabic(self):
        from whatsapp.language_detect import detect_language
        self.assertEqual(detect_language("   "), "ar")

    def test_numbers_only_defaults_en(self):
        from whatsapp.language_detect import detect_language
        self.assertEqual(detect_language("01-123456-01"), "en")

    def test_arabic_greeting(self):
        from whatsapp.language_detect import detect_language
        self.assertEqual(detect_language("السلام عليكم"), "ar")


# ---------------------------------------------------------------------------
# D. Language-Aware Registration Tests
# ---------------------------------------------------------------------------

class LanguageAwareRegistrationTest(TestCase):
    """Test language detection in the registration flow."""

    def setUp(self):
        cache.clear()

    @patch("whatsapp.tasks.send_text")
    def test_english_user_gets_english_onboarding(self, mock_send):
        _process_message_logic("+962796100001", "Hello")
        mock_send.assert_called_once_with("+962796100001", ONBOARDING_EN)

    @patch("whatsapp.tasks.send_text")
    def test_arabic_user_gets_arabic_onboarding(self, mock_send):
        _process_message_logic("+962796100002", "مرحبا")
        mock_send.assert_called_once_with("+962796100002", ONBOARDING_AR)

    @patch("whatsapp.tasks.send_text")
    def test_english_registration_success(self, mock_send):
        _handle_registration("+962796100003", "01-610003-01", "en")
        call_text = mock_send.call_args[0][1]
        self.assertIn("Registration successful", call_text)

    @patch("whatsapp.tasks.send_text")
    def test_arabic_registration_success(self, mock_send):
        _handle_registration("+962796100004", "01-610004-01", "ar")
        call_text = mock_send.call_args[0][1]
        self.assertIn("تم تسجيلك بنجاح", call_text)

    @patch("whatsapp.tasks.send_text")
    def test_subscriber_language_saved_on_registration(self, mock_send):
        _handle_registration("+962796100005", "01-610005-01", "en")
        sub = Subscriber.objects.get(phone_number="+962796100005")
        self.assertEqual(sub.language, "en")

    @patch("whatsapp.tasks.send_text")
    @patch("agent.coach.EnergyDetective.handle_message", side_effect=Exception("boom"))
    def test_english_fallback_on_error(self, mock_agent, mock_send):
        Subscriber.objects.create(
            subscription_number="01-610006-01",
            phone_number="+962796100006",
        )
        _process_message_logic("+962796100006", "Hello there")
        call_text = mock_send.call_args[0][1]
        self.assertIn("technical issue", call_text)


# ---------------------------------------------------------------------------
# E. Agent Error Handling Tests
# ---------------------------------------------------------------------------

class AgentErrorHandlingTest(TestCase):
    """Test agent/coach.py error handling."""

    @patch("core.llm_client._get_client")
    def test_llm_failure_returns_fallback_ar(self, mock_get_client):
        from agent.coach import EnergyDetective
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        # Intent classification succeeds (returns Arabic)
        mock_client.chat.completions.create.side_effect = [
            _mock_groq_response('{"intent":"general","confidence":0.9,"language":"ar"}'),
            Exception("API down"),
            Exception("API down"),  # retry also fails
        ]
        agent = EnergyDetective()
        result = agent.handle_message("+962790000001", "مرحبا")
        self.assertIn("مشكلة تقنية", result)

    @patch("core.llm_client._get_client")
    def test_llm_failure_returns_fallback_en(self, mock_get_client):
        from agent.coach import EnergyDetective
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [
            _mock_groq_response('{"intent":"general","confidence":0.9,"language":"en"}'),
            Exception("API down"),
            Exception("API down"),
        ]
        agent = EnergyDetective()
        result = agent.handle_message("+962790000001", "Hello")
        self.assertIn("technical issue", result)

    @patch("core.llm_client._get_client")
    def test_intent_classification_failure_uses_default(self, mock_get_client):
        from agent.coach import EnergyDetective
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        # Intent classification fails, then main call succeeds
        mock_client.chat.completions.create.side_effect = [
            Exception("classify failed"),
            Exception("classify failed"),  # retry
            _mock_groq_response("Hello! How can I help?"),
        ]
        agent = EnergyDetective()
        result = agent.handle_message("+962790000001", "Hi")
        self.assertEqual(result, "Hello! How can I help?")

    @patch("core.llm_client._get_client")
    def test_long_message_truncated(self, mock_get_client):
        from agent.coach import EnergyDetective, MAX_USER_MESSAGE_LENGTH
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_groq_response("OK")

        agent = EnergyDetective()
        long_msg = "A" * 10000
        agent.handle_message("+962790000001", long_msg)

        # Check that the user message in history was truncated
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args[1]["messages"] if "messages" in call_args[1] else call_args[0][0]
        # Find the user message (last non-system message in first call)
        user_msgs = [m for m in messages if m.get("role") == "user"]
        if user_msgs:
            self.assertLessEqual(len(user_msgs[-1]["content"]), MAX_USER_MESSAGE_LENGTH)

    @patch("core.llm_client._get_client")
    def test_conversation_state_saved_on_llm_failure(self, mock_get_client):
        from agent.coach import EnergyDetective
        from agent.conversation import ConversationManager
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [
            _mock_groq_response('{"intent":"general","confidence":0.9,"language":"ar"}'),
            Exception("down"),
            Exception("down"),
        ]
        agent = EnergyDetective()
        agent.handle_message("+962790099001", "test")
        # State should be saved even on failure
        state = ConversationManager().get_state("+962790099001")
        self.assertGreater(len(state.get("messages", [])), 0)

    @patch("core.llm_client._get_client")
    def test_malformed_tool_args_handled(self, mock_get_client):
        from agent.coach import EnergyDetective

        tc = MagicMock()
        tc.id = "call_1"
        tc.function.name = "get_consumption_summary"
        tc.function.arguments = "not valid json{{"

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [
            _mock_groq_response('{"intent":"general","confidence":0.9,"language":"en"}'),
            _mock_groq_response("", finish_reason="tool_calls", tool_calls=[tc]),
            _mock_groq_response("I had trouble with that tool, but here's what I know."),
        ]
        agent = EnergyDetective()
        result = agent.handle_message("+962790000001", "What's my usage?")
        self.assertNotIn("مشكلة تقنية", result)
        self.assertIsInstance(result, str)

    @patch("core.llm_client._get_client")
    def test_tool_execution_error_handled(self, mock_get_client):
        from agent.coach import EnergyDetective

        tc = MagicMock()
        tc.id = "call_2"
        tc.function.name = "get_consumption_summary"
        tc.function.arguments = '{"phone": "+962790000001"}'

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [
            _mock_groq_response('{"intent":"general","confidence":0.9,"language":"en"}'),
            _mock_groq_response("", finish_reason="tool_calls", tool_calls=[tc]),
            _mock_groq_response("Sorry, I couldn't retrieve your data."),
        ]
        agent = EnergyDetective()
        # Subscriber doesn't exist, so execute_tool will return an error
        result = agent.handle_message("+962790000001", "Show my usage")
        self.assertIsInstance(result, str)
        self.assertNotIn("مشكلة تقنية", result)

    def test_llm_error_exception_exists(self):
        from core.llm_client import LLMError
        self.assertTrue(issubclass(LLMError, Exception))

    @patch("core.llm_client._get_client")
    def test_llm_retry_on_transient_error(self, mock_get_client):
        from core.llm_client import chat_with_tools
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        # First call fails, second succeeds
        mock_client.chat.completions.create.side_effect = [
            Exception("transient error"),
            _mock_groq_response("Success after retry"),
        ]
        result = chat_with_tools(
            messages=[{"role": "user", "content": "Hi"}],
            system="You are helpful.",
        )
        self.assertEqual(result.choices[0].message.content, "Success after retry")
        self.assertEqual(mock_client.chat.completions.create.call_count, 2)

    @patch("core.llm_client._get_client")
    def test_llm_raises_after_max_retries(self, mock_get_client):
        from core.llm_client import chat_with_tools, LLMError
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("persistent failure")
        with self.assertRaises(LLMError):
            chat_with_tools(
                messages=[{"role": "user", "content": "Hi"}],
                system="You are helpful.",
            )

    @patch("core.llm_client._get_client")
    def test_classify_fast_retry_on_error(self, mock_get_client):
        from core.llm_client import classify_fast
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [
            Exception("fail"),
            _mock_groq_response("result text"),
        ]
        result = classify_fast("test prompt")
        self.assertEqual(result, "result text")


# ---------------------------------------------------------------------------
# F. Demo Command Tests
# ---------------------------------------------------------------------------

class DemoCommandTest(TestCase):
    """Test seed/management/commands/run_demo.py."""

    def test_scripted_mode_runs(self):
        out = StringIO()
        call_command("run_demo", stdout=out)
        output = out.getvalue()
        self.assertIn("Demo 1", output)
        self.assertIn("Demo 2", output)
        self.assertIn("Demo 3", output)

    def test_scripted_mode_outputs_conversations(self):
        out = StringIO()
        call_command("run_demo", stdout=out)
        output = out.getvalue()
        self.assertIn("مرحبا", output)
        self.assertIn("Hi", output)

    def test_scenario_filter(self):
        out = StringIO()
        call_command("run_demo", "--scenario=2", stdout=out)
        output = out.getvalue()
        self.assertIn("Demo 2", output)
        self.assertNotIn("Demo 1", output)

    def test_invalid_scenario(self):
        err = StringIO()
        call_command("run_demo", "--scenario=99", stderr=err)
        self.assertIn("Invalid scenario", err.getvalue())

    def test_live_mode_without_subscribers(self):
        err = StringIO()
        call_command("run_demo", "--live", stderr=err)
        self.assertIn("not found", err.getvalue())


# ---------------------------------------------------------------------------
# G. Message Templates Tests
# ---------------------------------------------------------------------------

class MessageTemplateTest(TestCase):
    """Test rate limit message templates."""

    def test_rate_limit_ar_exists(self):
        self.assertIsInstance(RATE_LIMIT_AR, str)
        self.assertGreater(len(RATE_LIMIT_AR), 0)

    def test_rate_limit_en_exists(self):
        self.assertIsInstance(RATE_LIMIT_EN, str)
        self.assertGreater(len(RATE_LIMIT_EN), 0)

    def test_all_templates_are_nonempty(self):
        templates = [
            ONBOARDING_AR, ONBOARDING_EN,
            REGISTRATION_SUCCESS_AR, REGISTRATION_SUCCESS_EN,
            FALLBACK_AR, FALLBACK_EN,
            WELCOME_BACK_AR, WELCOME_BACK_EN,
            RATE_LIMIT_AR, RATE_LIMIT_EN,
        ]
        for t in templates:
            self.assertGreater(len(t), 0, f"Template is empty: {t!r}")

"""
Phase 4 Tests — WhatsApp Integration (Twilio).

Tests cover:
- Webhook signature verification (Twilio RequestValidator)
- Webhook message extraction (form-encoded: From, Body, MessageSid, ButtonText)
- WhatsApp sender (Twilio SDK: send_text, send_buttons, send_list)
- Message processing (onboarding, registration, agent routing)
- Subscription number detection
- Celery fallback (sync processing when broker unavailable)
- Phone number normalization (including whatsapp: prefix)
- Edge cases (deduplication, errors, empty messages)
"""

from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import Subscriber
from meter.models import MeterReading
from whatsapp.tasks import (
    _normalize_phone,
    _looks_like_subscription_number,
    _process_message_logic,
    _send_split_text,
    _handle_registration,
    dispatch_message,
)
from whatsapp.message_templates import (
    ONBOARDING_AR, ONBOARDING_EN,
    REGISTRATION_SUCCESS_AR,
    REGISTRATION_CONFLICT_AR,
    WELCOME_BACK_AR,
    FALLBACK_EN,
)


WEBHOOK_URL = "/api/whatsapp/webhook/"


# ─── Webhook Signature Tests (Twilio RequestValidator) ───────────────


class WebhookSignatureTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    @override_settings(TWILIO_AUTH_TOKEN="test-auth-token")
    @patch("whatsapp.webhook.RequestValidator")
    def test_valid_signature_passes(self, mock_validator_cls):
        mock_validator_cls.return_value.validate.return_value = True
        resp = self.client.post(
            WEBHOOK_URL,
            data={"From": "whatsapp:+962791000001", "Body": "hello", "MessageSid": "SM1"},
            HTTP_X_TWILIO_SIGNATURE="valid-sig",
        )
        self.assertEqual(resp.status_code, 200)
        mock_validator_cls.assert_called_once_with("test-auth-token")

    @override_settings(TWILIO_AUTH_TOKEN="test-auth-token")
    @patch("whatsapp.webhook.RequestValidator")
    def test_invalid_signature_returns_401(self, mock_validator_cls):
        mock_validator_cls.return_value.validate.return_value = False
        resp = self.client.post(
            WEBHOOK_URL,
            data={"From": "whatsapp:+962791000001", "Body": "hello", "MessageSid": "SM1"},
            HTTP_X_TWILIO_SIGNATURE="bad-sig",
        )
        self.assertEqual(resp.status_code, 401)

    @override_settings(TWILIO_AUTH_TOKEN="test-auth-token")
    def test_missing_signature_returns_401(self):
        resp = self.client.post(
            WEBHOOK_URL,
            data={"From": "whatsapp:+962791000001", "Body": "hello"},
        )
        self.assertEqual(resp.status_code, 401)

    @override_settings(TWILIO_AUTH_TOKEN="")
    def test_empty_auth_token_skips_verification(self):
        """Dev mode: no auth token configured, all requests pass."""
        with patch("whatsapp.webhook.dispatch_message"):
            resp = self.client.post(
                WEBHOOK_URL,
                data={"From": "whatsapp:+962791000001", "Body": "hello", "MessageSid": "SM1"},
            )
        self.assertEqual(resp.status_code, 200)

    @override_settings(TWILIO_AUTH_TOKEN="test-auth-token")
    @patch("whatsapp.webhook.RequestValidator")
    def test_validator_receives_correct_params(self, mock_validator_cls):
        """RequestValidator.validate() receives URL, POST dict, and signature."""
        mock_validator_cls.return_value.validate.return_value = True
        with patch("whatsapp.webhook.dispatch_message"):
            self.client.post(
                WEBHOOK_URL,
                data={"From": "whatsapp:+962791000001", "Body": "test", "MessageSid": "SM1"},
                HTTP_X_TWILIO_SIGNATURE="test-sig",
            )
        validate_call = mock_validator_cls.return_value.validate
        validate_call.assert_called_once()
        args = validate_call.call_args[0]
        self.assertIn("/api/whatsapp/webhook/", args[0])  # URL
        self.assertIsInstance(args[1], dict)  # POST vars
        self.assertEqual(args[2], "test-sig")  # Signature


# ─── Webhook Message Extraction Tests (Form-Encoded) ─────────────────


@override_settings(TWILIO_AUTH_TOKEN="")
class WebhookMessageExtractionTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch("whatsapp.webhook.dispatch_message")
    def test_text_message_dispatches(self, mock_dispatch):
        self.client.post(WEBHOOK_URL, data={
            "From": "whatsapp:+962791000001",
            "Body": "hello",
            "MessageSid": "SMtest123",
        })
        mock_dispatch.assert_called_once_with(
            "+962791000001", "hello", message_id="SMtest123",
        )

    @patch("whatsapp.webhook.dispatch_message")
    def test_phone_prefix_stripped(self, mock_dispatch):
        """whatsapp: prefix is stripped from From field."""
        self.client.post(WEBHOOK_URL, data={
            "From": "whatsapp:+962791000002",
            "Body": "test",
            "MessageSid": "SM2",
        })
        phone = mock_dispatch.call_args[0][0]
        self.assertEqual(phone, "+962791000002")

    @patch("whatsapp.webhook.dispatch_message")
    def test_button_text_preferred_over_body(self, mock_dispatch):
        """When ButtonText is present, it takes priority over Body."""
        self.client.post(WEBHOOK_URL, data={
            "From": "whatsapp:+962791000001",
            "Body": "original body",
            "ButtonText": "نعم",
            "MessageSid": "SM3",
        })
        text = mock_dispatch.call_args[0][1]
        self.assertEqual(text, "نعم")

    @patch("whatsapp.webhook.dispatch_message")
    def test_body_used_when_no_button_text(self, mock_dispatch):
        self.client.post(WEBHOOK_URL, data={
            "From": "whatsapp:+962791000001",
            "Body": "plain message",
            "MessageSid": "SM4",
        })
        text = mock_dispatch.call_args[0][1]
        self.assertEqual(text, "plain message")

    @patch("whatsapp.webhook.dispatch_message")
    def test_empty_body_ignored(self, mock_dispatch):
        resp = self.client.post(WEBHOOK_URL, data={
            "From": "whatsapp:+962791000001",
            "Body": "",
            "MessageSid": "SM5",
        })
        self.assertEqual(resp.status_code, 200)
        mock_dispatch.assert_not_called()

    @patch("whatsapp.webhook.dispatch_message")
    def test_missing_from_ignored(self, mock_dispatch):
        resp = self.client.post(WEBHOOK_URL, data={
            "Body": "hello",
            "MessageSid": "SM6",
        })
        self.assertEqual(resp.status_code, 200)
        mock_dispatch.assert_not_called()

    @patch("whatsapp.webhook.dispatch_message")
    def test_message_sid_passed_as_id(self, mock_dispatch):
        self.client.post(WEBHOOK_URL, data={
            "From": "whatsapp:+962791000001",
            "Body": "test",
            "MessageSid": "SM_unique_789",
        })
        call_kwargs = mock_dispatch.call_args[1]
        self.assertEqual(call_kwargs["message_id"], "SM_unique_789")

    @patch("whatsapp.webhook.dispatch_message")
    def test_phone_without_whatsapp_prefix(self, mock_dispatch):
        """From without whatsapp: prefix still works."""
        self.client.post(WEBHOOK_URL, data={
            "From": "+962791000003",
            "Body": "test",
            "MessageSid": "SM7",
        })
        phone = mock_dispatch.call_args[0][0]
        self.assertEqual(phone, "+962791000003")

    def test_get_method_not_allowed(self):
        """Twilio webhook only accepts POST, no GET verification."""
        resp = self.client.get(WEBHOOK_URL)
        self.assertEqual(resp.status_code, 405)


# ─── Sender Tests (Twilio SDK) ───────────────────────────────────────


@override_settings(
    TWILIO_ACCOUNT_SID="ACtest123",
    TWILIO_AUTH_TOKEN="test-auth-token",
    TWILIO_WHATSAPP_NUMBER="whatsapp:+14155238886",
)
class SenderTest(TestCase):

    @patch("whatsapp.sender.Client")
    def test_send_text_calls_twilio(self, mock_client_cls):
        mock_msg = MagicMock(sid="SMresult123")
        mock_client_cls.return_value.messages.create.return_value = mock_msg
        from whatsapp.sender import send_text
        result = send_text("+962791000001", "Hello")
        self.assertEqual(result, "SMresult123")
        mock_client_cls.assert_called_once_with("ACtest123", "test-auth-token")

    @patch("whatsapp.sender.Client")
    def test_send_text_passes_correct_params(self, mock_client_cls):
        mock_msg = MagicMock(sid="SM1")
        mock_client_cls.return_value.messages.create.return_value = mock_msg
        from whatsapp.sender import send_text
        send_text("+962791000001", "test message")
        mock_client_cls.return_value.messages.create.assert_called_once_with(
            from_="whatsapp:+14155238886",
            body="test message",
            to="whatsapp:+962791000001",
        )

    @patch("whatsapp.sender.Client")
    def test_send_text_adds_whatsapp_prefix(self, mock_client_cls):
        mock_msg = MagicMock(sid="SM1")
        mock_client_cls.return_value.messages.create.return_value = mock_msg
        from whatsapp.sender import send_text
        send_text("+962791000001", "test")
        call_kwargs = mock_client_cls.return_value.messages.create.call_args[1]
        self.assertTrue(call_kwargs["to"].startswith("whatsapp:"))

    @patch("whatsapp.sender.Client")
    def test_send_buttons_renders_numbered_text(self, mock_client_cls):
        mock_msg = MagicMock(sid="SM1")
        mock_client_cls.return_value.messages.create.return_value = mock_msg
        from whatsapp.sender import send_buttons
        buttons = [
            {"id": "yes", "title": "نعم"},
            {"id": "no", "title": "لا"},
        ]
        send_buttons("+962791000001", "هل تريد؟", buttons)
        call_kwargs = mock_client_cls.return_value.messages.create.call_args[1]
        body = call_kwargs["body"]
        self.assertIn("هل تريد؟", body)
        self.assertIn("1. نعم", body)
        self.assertIn("2. لا", body)

    @patch("whatsapp.sender.Client")
    def test_send_buttons_limits_to_three(self, mock_client_cls):
        mock_msg = MagicMock(sid="SM1")
        mock_client_cls.return_value.messages.create.return_value = mock_msg
        from whatsapp.sender import send_buttons
        buttons = [
            {"id": "a", "title": "A"},
            {"id": "b", "title": "B"},
            {"id": "c", "title": "C"},
            {"id": "d", "title": "D"},
        ]
        send_buttons("+962791000001", "body", buttons)
        call_kwargs = mock_client_cls.return_value.messages.create.call_args[1]
        body = call_kwargs["body"]
        self.assertIn("3. C", body)
        self.assertNotIn("4. D", body)

    @patch("whatsapp.sender.Client")
    def test_send_list_renders_numbered_text(self, mock_client_cls):
        mock_msg = MagicMock(sid="SM1")
        mock_client_cls.return_value.messages.create.return_value = mock_msg
        from whatsapp.sender import send_list
        sections = [{"title": "Options", "rows": [
            {"id": "1", "title": "Option 1", "description": "Desc 1"},
            {"id": "2", "title": "Option 2", "description": "Desc 2"},
        ]}]
        send_list("+962791000001", "Choose:", "Menu", sections)
        call_kwargs = mock_client_cls.return_value.messages.create.call_args[1]
        body = call_kwargs["body"]
        self.assertIn("Choose:", body)
        self.assertIn("*Options*", body)
        self.assertIn("1. Option 1 — Desc 1", body)
        self.assertIn("2. Option 2 — Desc 2", body)

    @patch("whatsapp.sender.Client")
    def test_send_failure_returns_none(self, mock_client_cls):
        from twilio.base.exceptions import TwilioRestException
        mock_client_cls.return_value.messages.create.side_effect = TwilioRestException(
            status=400, uri="/test", msg="Bad Request",
        )
        from whatsapp.sender import send_text
        result = send_text("+962791000001", "test")
        self.assertIsNone(result)

    @patch("whatsapp.sender.Client")
    def test_unexpected_error_returns_none(self, mock_client_cls):
        mock_client_cls.return_value.messages.create.side_effect = ConnectionError("timeout")
        from whatsapp.sender import send_text
        result = send_text("+962791000001", "test")
        self.assertIsNone(result)


# ─── Subscription Number Detection Tests ──────────────────────────────


class SubscriptionNumberDetectionTest(TestCase):

    def test_valid_pattern(self):
        self.assertTrue(_looks_like_subscription_number("01-123456-01"))

    def test_valid_pattern_different_numbers(self):
        self.assertTrue(_looks_like_subscription_number("99-999999-99"))

    def test_rejects_letters(self):
        self.assertFalse(_looks_like_subscription_number("AB-123456-01"))

    def test_rejects_no_dashes(self):
        self.assertFalse(_looks_like_subscription_number("0112345601"))

    def test_rejects_partial(self):
        self.assertFalse(_looks_like_subscription_number("01-12345-01"))

    def test_rejects_extra_chars(self):
        self.assertFalse(_looks_like_subscription_number("01-123456-011"))


# ─── Phone Normalization Tests ────────────────────────────────────────


class PhoneNormalizationTest(TestCase):

    def test_adds_plus_prefix(self):
        self.assertEqual(_normalize_phone("962791000001"), "+962791000001")

    def test_preserves_existing_plus(self):
        self.assertEqual(_normalize_phone("+962791000001"), "+962791000001")

    def test_strips_whatsapp_prefix(self):
        self.assertEqual(_normalize_phone("whatsapp:+962791000001"), "+962791000001")

    def test_strips_whatsapp_and_adds_plus(self):
        self.assertEqual(_normalize_phone("whatsapp:962791000001"), "+962791000001")

    def test_normalized_phone_matches_subscriber(self):
        Subscriber.objects.create(
            subscription_number="01-999999-01",
            phone_number="+962791000099",
        )
        normalized = _normalize_phone("962791000099")
        exists = Subscriber.objects.filter(phone_number=normalized).exists()
        self.assertTrue(exists)


# ─── Message Processing Tests ─────────────────────────────────────────


class MessageProcessingTest(TestCase):

    @patch("whatsapp.tasks.send_text")
    def test_new_user_gets_onboarding(self, mock_send):
        _process_message_logic("+962790000099", "مرحبا")
        mock_send.assert_called_once_with("+962790000099", ONBOARDING_AR)

    @patch("whatsapp.tasks.send_text")
    def test_subscription_number_triggers_registration(self, mock_send):
        _process_message_logic("+962790000088", "01-888888-01")
        self.assertTrue(
            Subscriber.objects.filter(subscription_number="01-888888-01").exists()
        )

    @patch("whatsapp.tasks.send_text")
    def test_registration_creates_subscriber(self, mock_send):
        _process_message_logic("+962790000077", "01-777777-01")
        sub = Subscriber.objects.get(phone_number="+962790000077")
        self.assertEqual(sub.subscription_number, "01-777777-01")
        self.assertEqual(sub.tariff_category, "residential")
        self.assertTrue(sub.is_verified)

    @patch("whatsapp.tasks.send_text")
    def test_registration_generates_meter_data(self, mock_send):
        _process_message_logic("+962790000066", "01-666666-01")
        sub = Subscriber.objects.get(phone_number="+962790000066")
        readings_count = MeterReading.objects.filter(subscriber=sub).count()
        self.assertGreater(readings_count, 0)

    @patch("whatsapp.tasks.send_text")
    def test_registration_sends_success(self, mock_send):
        _process_message_logic("+962790000055", "01-555555-01")
        call_text = mock_send.call_args[0][1]
        self.assertIn("01-555555-01", call_text)

    @patch("whatsapp.tasks.send_text")
    def test_duplicate_subscription_different_phone(self, mock_send):
        Subscriber.objects.create(
            subscription_number="01-444444-01",
            phone_number="+962790000044",
        )
        _process_message_logic("+962790000043", "01-444444-01")
        call_text = mock_send.call_args[0][1]
        self.assertIn("01-444444-01", call_text)

    @patch("whatsapp.tasks.send_text")
    @patch("agent.coach.EnergyDetective.handle_message")
    def test_registered_user_sending_subscription_goes_to_agent(self, mock_agent, mock_send):
        """A registered user sending their subscription number gets routed to the agent."""
        Subscriber.objects.create(
            subscription_number="01-333333-01",
            phone_number="+962790000033",
        )
        mock_agent.return_value = "You're already registered!"
        _process_message_logic("+962790000033", "01-333333-01")
        mock_agent.assert_called_once()
        mock_send.assert_called_once_with("+962790000033", "You're already registered!")

    @patch("whatsapp.tasks.send_text")
    def test_welcome_back_same_phone_unregistered_path(self, mock_send):
        """If phone isn't found but subscription exists with same phone, welcome back."""
        Subscriber.objects.create(
            subscription_number="01-333333-01",
            phone_number="+962790000033",
        )
        _handle_registration("+962790000033", "01-333333-01")
        mock_send.assert_called_once_with("+962790000033", WELCOME_BACK_AR)

    @patch("whatsapp.tasks.send_text")
    @patch("agent.coach.EnergyDetective.handle_message")
    def test_registered_user_gets_agent_response(self, mock_agent, mock_send):
        Subscriber.objects.create(
            subscription_number="01-222222-01",
            phone_number="+962790000022",
        )
        mock_agent.return_value = "Your bill is 50 JOD"
        _process_message_logic("+962790000022", "ليش فاتورتي غالية؟")
        mock_send.assert_called_once_with("+962790000022", "Your bill is 50 JOD")

    @patch("whatsapp.tasks.send_text")
    def test_long_reply_split(self, mock_send):
        """Replies over 4000 chars should be split into multiple messages."""
        long_text = "A" * 3000 + "\n\n" + "B" * 3000
        _send_split_text("+962790000011", long_text)
        self.assertEqual(mock_send.call_count, 2)

    @patch("whatsapp.tasks.send_text")
    def test_long_reply_no_paragraph_break(self, mock_send):
        """When no paragraph break, split at last newline."""
        long_text = ("A" * 100 + "\n") * 50  # 5050 chars, many single newlines
        _send_split_text("+962790000010", long_text)
        self.assertGreaterEqual(mock_send.call_count, 2)


# ─── Celery Fallback Tests ────────────────────────────────────────────


class CeleryFallbackTest(TestCase):

    @patch("whatsapp.tasks._process_message_logic")
    @patch("whatsapp.tasks.process_incoming_message_task.delay")
    def test_dispatch_uses_delay(self, mock_delay, mock_logic):
        dispatch_message("+962791000001", "hello")
        mock_delay.assert_called_once_with("+962791000001", "hello")
        mock_logic.assert_not_called()

    @patch("whatsapp.tasks._process_message_logic")
    @patch("whatsapp.tasks.process_incoming_message_task.delay")
    def test_dispatch_falls_back_on_error(self, mock_delay, mock_logic):
        mock_delay.side_effect = Exception("Broker unavailable")
        dispatch_message("+962791000001", "hello")
        mock_logic.assert_called_once_with("+962791000001", "hello")

    @patch("whatsapp.tasks.send_text")
    def test_sync_processing_works(self, mock_send):
        """End-to-end sync: new user gets onboarding message."""
        _process_message_logic("+962790009999", "hi there")
        mock_send.assert_called_once_with("+962790009999", ONBOARDING_EN)


# ─── Edge Case Tests ──────────────────────────────────────────────────


@override_settings(TWILIO_AUTH_TOKEN="")
class EdgeCaseTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch("whatsapp.webhook.dispatch_message")
    def test_empty_text_ignored(self, mock_dispatch):
        """Message with empty body should not dispatch."""
        resp = self.client.post(WEBHOOK_URL, data={
            "From": "whatsapp:+962791000001",
            "Body": "",
            "MessageSid": "SM_empty",
        })
        self.assertEqual(resp.status_code, 200)
        mock_dispatch.assert_not_called()

    @patch("whatsapp.tasks.send_text")
    @patch("agent.coach.EnergyDetective.handle_message")
    def test_agent_exception_sends_fallback(self, mock_agent, mock_send):
        Subscriber.objects.create(
            subscription_number="01-111111-01",
            phone_number="+962790000011",
        )
        mock_agent.side_effect = RuntimeError("LLM timeout")
        _process_message_logic("+962790000011", "hello")
        mock_send.assert_called_with("+962790000011", FALLBACK_EN)

    def test_webhook_post_invalid_form_data(self):
        resp = self.client.post(
            WEBHOOK_URL,
            data="not valid form data",
            content_type="application/json",
        )
        # DRF with FormParser may return 415 (unsupported media type) or 200
        self.assertIn(resp.status_code, [200, 400, 415])

    @patch("whatsapp.tasks._process_message_logic")
    @patch("whatsapp.tasks.process_incoming_message_task.delay")
    def test_deduplication(self, mock_delay, mock_logic):
        """Same message_id should be processed only once."""
        from django.core.cache import cache
        cache.clear()
        dispatch_message("+962791000001", "hello", message_id="dup_unique_abc")
        dispatch_message("+962791000001", "hello", message_id="dup_unique_abc")
        self.assertEqual(mock_delay.call_count, 1)

    @patch("whatsapp.tasks.send_text")
    def test_empty_reply_not_sent(self, mock_send):
        """Empty agent reply should not trigger a send."""
        _send_split_text("+962790000001", "")
        mock_send.assert_not_called()

    @patch("whatsapp.tasks.send_text")
    def test_phone_normalization_in_processing(self, mock_send):
        """Phone without + prefix should be normalized during processing."""
        _process_message_logic("962790000088", "hi")
        mock_send.assert_called_once_with("+962790000088", ONBOARDING_EN)

    @patch("whatsapp.tasks.send_text")
    def test_subscription_with_spaces(self, mock_send):
        """Subscription number with spaces should still be recognized."""
        _process_message_logic("+962790000077", " 01-777777-01 ")
        self.assertTrue(
            Subscriber.objects.filter(subscription_number="01-777777-01").exists()
        )

    @patch("whatsapp.webhook.dispatch_message")
    def test_arabic_text_dispatches(self, mock_dispatch):
        """Arabic text in Body is correctly dispatched."""
        self.client.post(WEBHOOK_URL, data={
            "From": "whatsapp:+962791000001",
            "Body": "مرحبا كيف حالك",
            "MessageSid": "SM_arabic",
        })
        mock_dispatch.assert_called_once()
        text = mock_dispatch.call_args[0][1]
        self.assertEqual(text, "مرحبا كيف حالك")

    @patch("whatsapp.tasks.send_text")
    def test_whatsapp_prefix_normalized_in_processing(self, mock_send):
        """Phone with whatsapp: prefix gets normalized to +E.164."""
        _process_message_logic("whatsapp:+962790000088", "hi")
        mock_send.assert_called_once_with("+962790000088", ONBOARDING_EN)

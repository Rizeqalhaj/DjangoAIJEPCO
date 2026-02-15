"""WhatsApp webhook handler for Twilio."""

import logging

from django.conf import settings
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from twilio.request_validator import RequestValidator

from whatsapp.tasks import dispatch_message

logger = logging.getLogger(__name__)


@api_view(["POST"])
@parser_classes([FormParser, MultiPartParser])
def whatsapp_webhook(request):
    """
    Twilio WhatsApp webhook endpoint.

    Receives form-encoded POST with fields:
        From, Body, MessageSid, NumMedia, ProfileName, ButtonText, etc.
    """
    if not verify_twilio_signature(request):
        logger.warning("Invalid Twilio webhook signature")
        return Response({"error": "Invalid signature"}, status=401)

    phone = request.data.get("From", "")
    body = request.data.get("Body", "")
    message_sid = request.data.get("MessageSid", "")
    button_text = request.data.get("ButtonText", "")

    # Strip 'whatsapp:' prefix from phone
    phone = _strip_whatsapp_prefix(phone)

    # Prefer button text over body (interactive reply)
    text = button_text or body

    if not phone or not text:
        return Response({"status": "ignored"}, status=200)

    logger.info("Received message from %s: %s", phone, text[:50])
    dispatch_message(phone, text, message_id=message_sid)

    return Response({"status": "ok"}, status=200)


def verify_twilio_signature(request) -> bool:
    """
    Verify X-Twilio-Signature header.

    Returns True if signature is valid, or if no auth token is configured (dev mode).
    """
    auth_token = settings.TWILIO_AUTH_TOKEN
    if not auth_token:
        return True

    signature = request.headers.get("X-Twilio-Signature", "")
    if not signature:
        return False

    validator = RequestValidator(auth_token)
    url = request.build_absolute_uri()
    # Behind a reverse proxy (ngrok), Django sees http:// but Twilio signs with https://
    if request.headers.get("X-Forwarded-Proto") == "https" and url.startswith("http://"):
        url = "https://" + url[len("http://"):]
    post_vars = request.POST.dict()

    return validator.validate(url, post_vars, signature)


def _strip_whatsapp_prefix(phone: str) -> str:
    """Strip 'whatsapp:' prefix from Twilio phone format."""
    if phone.startswith("whatsapp:"):
        return phone[len("whatsapp:"):]
    return phone

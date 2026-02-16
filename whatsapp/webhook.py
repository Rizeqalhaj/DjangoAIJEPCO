"""WhatsApp webhook handler for Twilio."""

import logging

from django.conf import settings
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from twilio.request_validator import RequestValidator

from whatsapp.tasks import dispatch_message
from whatsapp.transcriber import transcribe_audio
from whatsapp.sender import send_text
from whatsapp.language_detect import detect_language
from whatsapp.message_templates import (
    VOICE_TRANSCRIPTION_FAILED_AR,
    VOICE_TRANSCRIPTION_FAILED_EN,
)

logger = logging.getLogger(__name__)


@api_view(["POST"])
@parser_classes([FormParser, MultiPartParser])
def whatsapp_webhook(request):
    """
    Twilio WhatsApp webhook endpoint.

    Receives form-encoded POST with fields:
        From, Body, MessageSid, NumMedia, ProfileName, ButtonText, etc.
    For voice messages: NumMedia=1, MediaUrl0, MediaContentType0.
    """
    if not verify_twilio_signature(request):
        logger.warning("Invalid Twilio webhook signature")
        return Response({"error": "Invalid signature"}, status=401)

    phone = request.data.get("From", "")
    body = request.data.get("Body", "")
    message_sid = request.data.get("MessageSid", "")
    button_text = request.data.get("ButtonText", "")
    num_media = int(request.data.get("NumMedia", "0"))

    # Strip 'whatsapp:' prefix from phone
    phone = _strip_whatsapp_prefix(phone)

    # Prefer button text over body (interactive reply)
    text = button_text or body

    # Handle voice messages (audio media)
    if num_media > 0:
        media_type = request.data.get("MediaContentType0", "")
        media_url = request.data.get("MediaUrl0", "")
        if media_type.startswith("audio/") and media_url:
            logger.info("Voice message from %s (%s)", phone, media_type)
            transcribed = transcribe_audio(media_url, media_type)
            if transcribed:
                text = transcribed
            else:
                lang = detect_language(body) if body else "ar"
                send_text(phone, VOICE_TRANSCRIPTION_FAILED_AR if lang == "ar" else VOICE_TRANSCRIPTION_FAILED_EN)
                return Response({"status": "transcription_failed"}, status=200)

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
    # Behind a reverse proxy (Railway, ngrok), Django may see http:// but Twilio signs https://
    # Always upgrade to https for production URLs
    if url.startswith("http://") and not url.startswith("http://localhost"):
        url = "https://" + url[len("http://"):]
    post_vars = request.POST.dict()

    is_valid = validator.validate(url, post_vars, signature)
    if not is_valid:
        logger.warning("Signature validation failed. URL used: %s", url)
    return is_valid


def _strip_whatsapp_prefix(phone: str) -> str:
    """Strip 'whatsapp:' prefix from Twilio phone format."""
    if phone.startswith("whatsapp:"):
        return phone[len("whatsapp:"):]
    return phone

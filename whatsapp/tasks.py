"""WhatsApp message processing with Celery async / synchronous fallback."""

import logging
import re

from celery import shared_task
from django.core.cache import cache

from accounts.models import Subscriber
from agent.coach import EnergyDetective
from meter.generator import generate_meter_data
from meter.models import MeterReading
from whatsapp.sender import send_text
from whatsapp.rate_limiter import check_rate_limit
from whatsapp.language_detect import detect_language
from whatsapp.message_templates import (
    ONBOARDING_AR, ONBOARDING_EN,
    REGISTRATION_SUCCESS_AR, REGISTRATION_SUCCESS_EN,
    REGISTRATION_CONFLICT_AR, REGISTRATION_CONFLICT_EN,
    WELCOME_BACK_AR, WELCOME_BACK_EN,
    FALLBACK_AR, FALLBACK_EN,
    RATE_LIMIT_AR, RATE_LIMIT_EN,
)

logger = logging.getLogger(__name__)

SUBSCRIPTION_PATTERN = re.compile(r'^\d{2}-\d{6}-\d{2}$')
MAX_WHATSAPP_TEXT = 4000
DEFAULT_PROFILE = "ac_heavy_summer"
DEFAULT_DEMO_DAYS = 90
DEDUP_TTL = 300  # 5 minutes


@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def process_incoming_message_task(self, phone: str, text: str):
    """Celery task wrapper for message processing."""
    _process_message_logic(phone, text)


def dispatch_message(phone: str, text: str, message_id: str = ""):
    """
    Dispatch message to Celery if available, otherwise process synchronously.

    Args:
        phone: Sender phone number (may lack + prefix).
        text: Message text content.
        message_id: WhatsApp message ID for deduplication.
    """
    if message_id:
        dedup_key = f"wa_msg:{message_id}"
        if cache.get(dedup_key):
            logger.info("Duplicate message %s ignored", message_id)
            return
        cache.set(dedup_key, True, DEDUP_TTL)

    if _celery_worker_available():
        try:
            process_incoming_message_task.delay(phone, text)
            logger.info("Message dispatched to Celery for phone=%s", phone)
            return
        except Exception as exc:
            logger.warning(
                "Celery dispatch failed (%s), falling back to sync for phone=%s",
                type(exc).__name__, phone,
            )

    logger.info("Processing synchronously for phone=%s", phone)
    _process_message_logic(phone, text)


def _process_message_logic(phone: str, text: str):
    """Core message processing. Works both sync and async."""
    phone = _normalize_phone(phone)
    lang = detect_language(text)

    if not check_rate_limit(phone):
        send_text(phone, RATE_LIMIT_AR if lang == "ar" else RATE_LIMIT_EN)
        return

    try:
        try:
            subscriber = Subscriber.objects.get(phone_number=phone)
        except Subscriber.DoesNotExist:
            cleaned = text.strip().replace(" ", "")
            if _looks_like_subscription_number(cleaned):
                _handle_registration(phone, cleaned, lang)
            else:
                send_text(phone, ONBOARDING_AR if lang == "ar" else ONBOARDING_EN)
            return

        agent = EnergyDetective()
        reply = agent.handle_message(phone, text)
        _send_split_text(phone, reply)

    except Exception:
        logger.exception("Error processing message from %s", phone)
        send_text(phone, FALLBACK_AR if lang == "ar" else FALLBACK_EN)


def _handle_registration(phone: str, subscription_number: str, lang: str = "ar"):
    """
    Register a new subscriber or handle conflicts.

    Creates the subscriber, generates 90 days of demo meter data,
    and sends a success message in the detected language.
    """
    existing = Subscriber.objects.filter(
        subscription_number=subscription_number
    ).first()

    if existing:
        if existing.phone_number == phone:
            send_text(phone, WELCOME_BACK_AR if lang == "ar" else WELCOME_BACK_EN)
        else:
            template = REGISTRATION_CONFLICT_AR if lang == "ar" else REGISTRATION_CONFLICT_EN
            send_text(
                phone,
                template.format(subscription_number=subscription_number),
            )
        return

    subscriber = Subscriber.objects.create(
        subscription_number=subscription_number,
        phone_number=phone,
        tariff_category="residential",
        governorate="Amman",
        language=lang,
        is_verified=True,
    )

    readings = generate_meter_data(subscriber, DEFAULT_PROFILE, days=DEFAULT_DEMO_DAYS)
    MeterReading.objects.bulk_create(readings, batch_size=1000)
    logger.info(
        "Registered %s with %d readings", subscription_number, len(readings),
    )

    template = REGISTRATION_SUCCESS_AR if lang == "ar" else REGISTRATION_SUCCESS_EN
    send_text(
        phone,
        template.format(subscription_number=subscription_number),
    )


def _send_split_text(phone: str, text: str):
    """Send text, splitting into multiple messages if over WhatsApp limit."""
    if not text:
        return

    if len(text) <= MAX_WHATSAPP_TEXT:
        send_text(phone, text)
        return

    split_point = text[:MAX_WHATSAPP_TEXT].rfind("\n\n")
    if split_point == -1 or split_point < MAX_WHATSAPP_TEXT // 2:
        split_point = text[:MAX_WHATSAPP_TEXT].rfind("\n")
    if split_point == -1:
        split_point = MAX_WHATSAPP_TEXT

    send_text(phone, text[:split_point])
    remaining = text[split_point:].lstrip("\n")
    if remaining:
        _send_split_text(phone, remaining)


def _normalize_phone(phone: str) -> str:
    """Ensure phone has + prefix for E.164 format. Strips Twilio whatsapp: prefix."""
    if phone.startswith("whatsapp:"):
        phone = phone[len("whatsapp:"):]
    if not phone.startswith("+"):
        return f"+{phone}"
    return phone


def _celery_worker_available() -> bool:
    """Check if at least one Celery worker is consuming tasks. Cached for 60s."""
    cache_key = "celery_worker_available"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        from config.celery import app
        inspector = app.control.inspect(timeout=1.0)
        active = inspector.active_queues()
        available = bool(active)
    except Exception:
        available = False

    cache.set(cache_key, available, 60)
    return available


def _looks_like_subscription_number(text: str) -> bool:
    """Check if text matches JEPCO subscription number format XX-XXXXXX-XX."""
    return bool(SUBSCRIPTION_PATTERN.match(text))

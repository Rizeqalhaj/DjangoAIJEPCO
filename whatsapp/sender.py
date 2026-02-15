"""WhatsApp message sender using Twilio SDK.

When TWILIO_ACCOUNT_SID is not set, messages are logged to the console
instead of being sent (dry-run mode for local development).
"""

import logging

from django.conf import settings
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

logger = logging.getLogger(__name__)

MAX_BUTTONS = 3


def _is_dry_run() -> bool:
    """True when WHATSAPP_DRY_RUN=True or Twilio credentials are missing."""
    if getattr(settings, "WHATSAPP_DRY_RUN", False):
        return True
    return not getattr(settings, "TWILIO_ACCOUNT_SID", "")


def _get_client() -> Client:
    return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


def _to_whatsapp(phone: str) -> str:
    """Ensure phone is in Twilio whatsapp: format."""
    if not phone.startswith("whatsapp:"):
        return f"whatsapp:{phone}"
    return phone


def send_text(phone: str, text: str) -> str | None:
    """
    Send a plain text message via Twilio WhatsApp.

    Returns the message SID on success, None on failure.
    In dry-run mode (no Twilio creds), logs the message to console.
    Always prints the message to the terminal for visibility.
    """
    # Always print to terminal so messages are visible during development
    print(f"\n{'='*50}")
    print(f"📱 WhatsApp → {phone}")
    print(f"{'─'*50}")
    print(text)
    print(f"{'='*50}\n")

    if _is_dry_run():
        return "dry-run"

    try:
        client = _get_client()
        message = client.messages.create(
            from_=settings.TWILIO_WHATSAPP_NUMBER,
            body=text,
            to=_to_whatsapp(phone),
        )
        logger.info("[WhatsApp] Sent to %s (SID: %s)", phone, message.sid)
        return message.sid
    except TwilioRestException as exc:
        logger.error(
            "[WhatsApp] FAILED to %s — Twilio error %s: %s", phone, exc.status, exc.msg,
        )
        return None
    except Exception:
        logger.exception("Unexpected error sending WhatsApp message")
        return None


def send_buttons(phone: str, body: str, buttons: list[dict]) -> str | None:
    """
    Send a message with button options as numbered text.

    Twilio WhatsApp interactive buttons require pre-approved Content Templates.
    For dev/demo, we render buttons as a numbered text list.

    Args:
        phone: Recipient phone number.
        body: Message body text.
        buttons: List of {"id": str, "title": str} dicts. Max 3.
    """
    lines = [body, ""]
    for i, btn in enumerate(buttons[:MAX_BUTTONS], 1):
        lines.append(f"{i}. {btn['title']}")
    return send_text(phone, "\n".join(lines))


def send_list(
    phone: str,
    body: str,
    button_text: str,
    sections: list[dict],
) -> str | None:
    """
    Send a message with list options as numbered text.

    Twilio WhatsApp list messages require Content Templates.
    For dev/demo, we render as a numbered text list.

    Args:
        phone: Recipient phone number.
        body: Message body text.
        button_text: Ignored (no native list button in text fallback).
        sections: List of {"title": str, "rows": [{"id": str, "title": str, "description": str}]}.
    """
    lines = [body, ""]
    counter = 1
    for section in sections:
        if section.get("title"):
            lines.append(f"*{section['title']}*")
        for row in section.get("rows", []):
            desc = f" — {row['description']}" if row.get("description") else ""
            lines.append(f"{counter}. {row['title']}{desc}")
            counter += 1
    return send_text(phone, "\n".join(lines))

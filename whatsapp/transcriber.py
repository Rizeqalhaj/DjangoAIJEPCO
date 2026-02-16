"""Audio transcription for WhatsApp voice messages using Gemini."""

import logging
import tempfile
from pathlib import Path

import httpx
from django.conf import settings
from google import genai

logger = logging.getLogger(__name__)

TRANSCRIPTION_MODEL = "gemini-2.0-flash"
TRANSCRIPTION_PROMPT = "Transcribe this audio exactly. Return only the transcription, nothing else."
SUPPORTED_AUDIO_TYPES = {"audio/ogg", "audio/mpeg", "audio/mp4", "audio/wav", "audio/webm"}
MAX_AUDIO_BYTES = 20 * 1024 * 1024  # 20 MB (Gemini limit)

# Map MIME types to file extensions for temp files
_EXT_MAP = {
    "audio/ogg": ".ogg",
    "audio/mpeg": ".mp3",
    "audio/mp4": ".m4a",
    "audio/wav": ".wav",
    "audio/webm": ".webm",
}


def transcribe_audio(media_url: str, content_type: str) -> str | None:
    """
    Download audio from Twilio and transcribe via Gemini.

    Args:
        media_url: Twilio media URL (pre-signed, expires ~1 hour).
        content_type: MIME type (e.g. "audio/ogg").

    Returns:
        Transcribed text, or None on any failure.
    """
    if content_type not in SUPPORTED_AUDIO_TYPES:
        logger.warning("[Transcribe] Unsupported audio type: %s", content_type)
        return None

    tmp_path = None
    uploaded_file = None
    try:
        tmp_path = _download_audio(media_url, content_type)
        if not tmp_path:
            return None

        if tmp_path.stat().st_size > MAX_AUDIO_BYTES:
            logger.warning("[Transcribe] Audio too large: %d bytes", tmp_path.stat().st_size)
            return None

        client = genai.Client(api_key=settings.GEMINI_API_KEY)

        uploaded_file = client.files.upload(file=tmp_path, config={"mime_type": content_type})
        logger.info("[Transcribe] Uploaded %s (%s)", uploaded_file.name, content_type)

        response = client.models.generate_content(
            model=TRANSCRIPTION_MODEL,
            contents=[uploaded_file, TRANSCRIPTION_PROMPT],
        )

        text = response.text.strip() if response.text else None
        if text:
            logger.info("[Transcribe] Result (%d chars): %s", len(text), text[:80])
        else:
            logger.warning("[Transcribe] Empty transcription result")

        return text

    except Exception:
        logger.exception("[Transcribe] Failed to transcribe audio")
        return None

    finally:
        if uploaded_file:
            try:
                client.files.delete(name=uploaded_file.name)
            except Exception:
                logger.debug("[Transcribe] Failed to delete uploaded file")
        if tmp_path and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def _download_audio(media_url: str, content_type: str) -> Path | None:
    """Download audio from Twilio URL to a temp file."""
    ext = _EXT_MAP.get(content_type, ".ogg")
    try:
        with httpx.Client(timeout=30.0) as http:
            response = http.get(
                media_url,
                auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
                follow_redirects=True,
            )
            response.raise_for_status()

        tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
        tmp.write(response.content)
        tmp.close()

        logger.info("[Transcribe] Downloaded %d bytes to %s", len(response.content), tmp.name)
        return Path(tmp.name)

    except Exception:
        logger.exception("[Transcribe] Failed to download audio from %s", media_url)
        return None

"""LLM client wrapper — uses Groq (free) for development."""

import logging

from groq import Groq
from django.conf import settings

logger = logging.getLogger(__name__)

MAIN_MODEL = "llama-3.3-70b-versatile"
FAST_MODEL = "llama-3.1-8b-instant"

MAX_LLM_RETRIES = 1


class LLMError(Exception):
    """Raised when LLM API call fails after retries."""
    pass


def _get_client():
    """Lazily create Groq client."""
    return Groq(api_key=settings.GROQ_API_KEY)


def chat_with_tools(
    messages: list,
    system: str,
    tools: list = None,
    model: str = MAIN_MODEL,
    max_tokens: int = 1024,
):
    """
    Send a message to the LLM with optional tool use.

    System prompt is injected as first message (OpenAI-compatible format).
    Retries once on transient errors. Raises LLMError on persistent failure.
    """
    full_messages = [{"role": "system", "content": system}] + messages

    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": full_messages,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    last_exc = None
    for attempt in range(MAX_LLM_RETRIES + 1):
        try:
            return _get_client().chat.completions.create(**kwargs)
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "LLM API call failed (attempt %d/%d): %s",
                attempt + 1, MAX_LLM_RETRIES + 1, exc,
            )

    raise LLMError(
        f"LLM API failed after {MAX_LLM_RETRIES + 1} attempts: {last_exc}"
    ) from last_exc


def classify_fast(prompt: str, system: str = "") -> str:
    """
    Quick classification using a fast model. Returns raw text response.

    Retries once on transient errors. Raises LLMError on persistent failure.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    last_exc = None
    for attempt in range(MAX_LLM_RETRIES + 1):
        try:
            response = _get_client().chat.completions.create(
                model=FAST_MODEL,
                max_tokens=200,
                messages=messages,
            )
            return response.choices[0].message.content
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "Fast classify failed (attempt %d/%d): %s",
                attempt + 1, MAX_LLM_RETRIES + 1, exc,
            )

    raise LLMError(
        f"Fast classify failed after {MAX_LLM_RETRIES + 1} attempts: {last_exc}"
    ) from last_exc

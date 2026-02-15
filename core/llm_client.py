"""LLM client wrapper — uses Gemini via OpenAI-compatible endpoint."""

import logging

from openai import OpenAI
from django.conf import settings

logger = logging.getLogger(__name__)

MAIN_MODEL = "gemini-2.0-flash"
FAST_MODEL = "gemini-2.0-flash"

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

MAX_LLM_RETRIES = 1


class LLMError(Exception):
    """Raised when LLM API call fails after retries."""
    pass


def _get_client():
    """Lazily create OpenAI client pointed at Gemini endpoint."""
    return OpenAI(
        api_key=settings.GEMINI_API_KEY,
        base_url=GEMINI_BASE_URL,
    )


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
            logger.debug("[LLM] API call: model=%s, msgs=%d, tools=%d",
                         model, len(full_messages), len(tools) if tools else 0)
            result = _get_client().chat.completions.create(**kwargs)
            logger.debug("[LLM] Response: finish_reason=%s, usage=%s",
                         result.choices[0].finish_reason,
                         f"{result.usage.prompt_tokens}in/{result.usage.completion_tokens}out"
                         if result.usage else "n/a")
            return result
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
    Quick classification using the fast model. Returns raw text response.

    Retries once on transient errors. Raises LLMError on persistent failure.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    last_exc = None
    for attempt in range(MAX_LLM_RETRIES + 1):
        try:
            logger.debug("[LLM] Fast classify: model=%s", FAST_MODEL)
            response = _get_client().chat.completions.create(
                model=FAST_MODEL,
                max_tokens=200,
                messages=messages,
            )
            logger.debug("[LLM] Fast result: %s", response.choices[0].message.content[:100])
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

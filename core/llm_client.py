"""LLM client wrapper — uses Groq (free) for development."""

from groq import Groq
from django.conf import settings

# Models
MAIN_MODEL = "llama-3.3-70b-versatile"
FAST_MODEL = "llama-3.1-8b-instant"


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
    Returns the full response object (caller handles tool-use loop).
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

    return _get_client().chat.completions.create(**kwargs)


def classify_fast(prompt: str, system: str = "") -> str:
    """
    Quick classification using a fast model. Returns raw text response.
    Used for intent detection and language classification.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = _get_client().chat.completions.create(
        model=FAST_MODEL,
        max_tokens=200,
        messages=messages,
    )
    return response.choices[0].message.content

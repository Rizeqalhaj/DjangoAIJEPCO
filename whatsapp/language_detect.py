"""Lightweight language detection for WhatsApp messages (no LLM needed)."""

import re

_ARABIC_PATTERN = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]')


def detect_language(text: str) -> str:
    """
    Detect whether a message is Arabic or English based on character analysis.

    Returns "ar" or "en".
    """
    if not text or not text.strip():
        return "ar"

    non_space = text.replace(" ", "")
    if not non_space:
        return "ar"

    arabic_chars = len(_ARABIC_PATTERN.findall(non_space))
    ratio = arabic_chars / len(non_space)

    return "ar" if ratio > 0.3 else "en"

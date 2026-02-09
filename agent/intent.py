"""Intent classifier using Claude Haiku for fast classification."""

import json
from core.llm_client import classify_fast

INTENT_SYSTEM = """You are an intent classifier for a Jordanian electricity usage optimization assistant called KahrabaAI.

Classify the user message into exactly ONE intent and detect the language.

Intents:
- onboarding: User is new, wants to register, or is providing their subscription number
- bill_query: User is asking about their bill, why it's high, cost breakdown
- usage_analysis: User wants to understand their consumption patterns, see spikes, trends
- optimization_request: User wants advice on how to reduce consumption or save money
- plan_check: User is checking progress on an existing optimization plan
- tariff_question: User asking about electricity prices, TOU periods, tariff tiers
- general: Greeting, thanks, or doesn't fit other categories

Respond ONLY with valid JSON:
{"intent": "bill_query", "confidence": 0.92, "language": "ar"}
"""

INTENTS = [
    "onboarding",
    "bill_query",
    "usage_analysis",
    "optimization_request",
    "plan_check",
    "tariff_question",
    "general",
]


def classify_intent(message: str) -> dict:
    """
    Classify a user message into an intent.

    Returns:
        {"intent": str, "confidence": float, "language": "ar"|"en"}
    """
    raw = classify_fast(
        prompt=f"User message: {message}",
        system=INTENT_SYSTEM,
    )
    try:
        result = json.loads(raw.strip())
        if result.get("intent") not in INTENTS:
            result["intent"] = "general"
        return result
    except (json.JSONDecodeError, KeyError):
        return {"intent": "general", "confidence": 0.5, "language": "ar"}

"""Conversation state manager using Django's cache framework."""

import json
from django.core.cache import cache


class ConversationManager:
    """
    Manages conversation state in Django cache.

    Each phone number gets a conversation state with 30-minute TTL.
    Works with LocMemCache (dev) or Redis (production) transparently.
    """

    TTL = 1800  # 30 minutes

    def _key(self, phone: str) -> str:
        return f"conv:{phone}"

    def get_state(self, phone: str) -> dict:
        """Get conversation state for a phone number."""
        data = cache.get(self._key(phone))
        if data:
            return json.loads(data)
        return {"messages": [], "language": "ar", "last_intent": None}

    def save_state(self, phone: str, state: dict):
        """Save conversation state with TTL."""
        cache.set(
            self._key(phone),
            json.dumps(state, ensure_ascii=False, default=str),
            self.TTL,
        )

    def clear_state(self, phone: str):
        """Clear conversation state."""
        cache.delete(self._key(phone))

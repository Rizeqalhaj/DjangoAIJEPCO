"""Conversation state manager using Django's cache framework with DB persistence."""

import json
import logging

from django.core.cache import cache

from core.clock import now as clock_now

logger = logging.getLogger(__name__)


class ConversationManager:
    """
    Manages conversation state in Django cache with DB fallback.

    Each phone number gets a conversation state with 30-minute TTL.
    On cache miss, reconstructs state from DB (last 10 turns of most recent session).
    Works with LocMemCache (dev) or Redis (production) transparently.
    """

    TTL = 1800  # 30 minutes

    def _key(self, phone: str) -> str:
        return f"conv:{phone}"

    def get_state(self, phone: str) -> dict:
        """Get conversation state for a phone number. Falls back to DB on cache miss."""
        data = cache.get(self._key(phone))
        if data:
            return json.loads(data)

        # Cache miss — try to reconstruct from DB
        return self._load_from_db(phone)

    def _load_from_db(self, phone: str) -> dict:
        """Reconstruct conversation state from DB for a phone number."""
        from accounts.models import Subscriber
        from agent.models import ConversationSession

        default_state = {"messages": [], "language": "ar", "last_intent": None}

        try:
            subscriber = Subscriber.objects.get(phone_number=phone)
        except Subscriber.DoesNotExist:
            return default_state

        session = (
            ConversationSession.objects
            .filter(subscriber=subscriber, is_active=True)
            .order_by('-created_at')
            .first()
        )

        if not session:
            return default_state

        # Check if session is expired (older than TTL)
        last_turn = session.turns.order_by('-created_at').first()
        last_activity = last_turn.created_at if last_turn else session.created_at
        age_seconds = (clock_now() - last_activity).total_seconds()

        if age_seconds > self.TTL:
            session.is_active = False
            session.ended_at = clock_now()
            session.save(update_fields=['is_active', 'ended_at', 'updated_at'])
            return default_state

        # Reconstruct messages from last 10 turns
        turns = list(session.turns.order_by('-created_at')[:10])
        turns.reverse()

        messages = []
        for turn in turns:
            messages.append({"role": "user", "content": turn.user_message})
            messages.append({"role": "assistant", "content": turn.agent_response})

        state = {
            "messages": messages,
            "language": session.language,
            "last_intent": session.last_intent,
        }

        # Warm the cache
        self.save_state(phone, state)

        logger.debug(
            "[ConversationManager] Reconstructed state from DB for %s: %d messages",
            phone, len(messages),
        )

        return state

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

    def save_turn(
        self,
        phone: str,
        user_message: str,
        agent_response: str,
        intent: str,
        tools_called: list,
        language: str,
        state: dict,
    ):
        """Persist a single conversation turn to the database."""
        from accounts.models import Subscriber
        from agent.models import ConversationSession, ConversationTurn

        try:
            subscriber = Subscriber.objects.get(phone_number=phone)
        except Subscriber.DoesNotExist:
            logger.debug("[ConversationManager] No subscriber for %s, skipping save_turn", phone)
            return

        # Get or create active session
        session = (
            ConversationSession.objects
            .filter(subscriber=subscriber, is_active=True)
            .order_by('-created_at')
            .first()
        )

        if session:
            # Check if session is expired
            last_turn = session.turns.order_by('-created_at').first()
            last_activity = last_turn.created_at if last_turn else session.created_at
            age_seconds = (clock_now() - last_activity).total_seconds()

            if age_seconds > self.TTL:
                session.is_active = False
                session.ended_at = clock_now()
                session.save(update_fields=['is_active', 'ended_at', 'updated_at'])
                session = None

        if not session:
            session = ConversationSession.objects.create(
                subscriber=subscriber,
                language=language,
                last_intent=intent or '',
            )

        # Update session metadata
        session.language = language
        session.last_intent = intent or ''
        session.save(update_fields=['language', 'last_intent', 'updated_at'])

        # Create the turn
        ConversationTurn.objects.create(
            session=session,
            user_message=user_message,
            agent_response=agent_response,
            intent=intent or '',
            tools_called=tools_called or [],
            language=language,
        )

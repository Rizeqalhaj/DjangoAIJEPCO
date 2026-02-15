"""Agent models for persistent conversation storage and subscriber notes."""

from django.db import models
from core.models import TimestampedModel


class ConversationSession(TimestampedModel):
    """A conversation session between a subscriber and the agent."""

    subscriber = models.ForeignKey(
        'accounts.Subscriber',
        on_delete=models.CASCADE,
        related_name='conversation_sessions',
    )
    language = models.CharField(max_length=2, default='ar')
    last_intent = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['subscriber', '-created_at']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"Session {self.id} — {self.subscriber} ({'active' if self.is_active else 'ended'})"


class ConversationTurn(TimestampedModel):
    """A single turn (user message + agent response) in a conversation session."""

    session = models.ForeignKey(
        ConversationSession,
        on_delete=models.CASCADE,
        related_name='turns',
    )
    user_message = models.TextField()
    agent_response = models.TextField()
    intent = models.CharField(max_length=30, blank=True)
    tools_called = models.JSONField(default=list)
    language = models.CharField(max_length=2, default='ar')

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['session', 'created_at']),
        ]

    def __str__(self):
        return f"Turn {self.id} in Session {self.session_id}"


class SubscriberNote(TimestampedModel):
    """A long-term memory note about a subscriber, learned from conversations."""

    CATEGORY_CHOICES = [
        ('appliance', 'Appliance'),
        ('schedule', 'Schedule'),
        ('preference', 'Preference'),
        ('household_fact', 'Household Fact'),
        ('goal', 'Goal'),
    ]

    subscriber = models.ForeignKey(
        'accounts.Subscriber',
        on_delete=models.CASCADE,
        related_name='notes',
    )
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    content = models.TextField(help_text="Stored in English for consistency")
    source_turn = models.ForeignKey(
        ConversationTurn,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notes_created',
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['subscriber', 'is_active', '-created_at']),
            models.Index(fields=['subscriber', 'category']),
        ]

    def __str__(self):
        return f"[{self.category}] {self.content[:60]}"

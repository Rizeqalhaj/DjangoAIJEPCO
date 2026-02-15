"""Service layer for subscriber notes (long-term memory)."""

import logging

from agent.models import SubscriberNote

logger = logging.getLogger(__name__)

MAX_ACTIVE_NOTES = 10


def save_note(subscriber, category: str, content: str, source_turn=None) -> SubscriberNote:
    """
    Create a new note for a subscriber.

    If 10+ active notes exist, deactivate the oldest to keep memory focused.
    """
    note = SubscriberNote.objects.create(
        subscriber=subscriber,
        category=category,
        content=content,
        source_turn=source_turn,
    )

    # Cap active notes at MAX_ACTIVE_NOTES
    active_notes = (
        SubscriberNote.objects
        .filter(subscriber=subscriber, is_active=True)
        .order_by('-created_at')
    )
    excess = list(active_notes[MAX_ACTIVE_NOTES:])
    if excess:
        excess_ids = [n.id for n in excess]
        SubscriberNote.objects.filter(id__in=excess_ids).update(is_active=False)
        logger.debug(
            "[Notes] Deactivated %d old notes for subscriber %s",
            len(excess_ids), subscriber.phone_number,
        )

    return note


def get_active_notes(subscriber) -> list[SubscriberNote]:
    """Return up to 10 active notes for a subscriber, newest first."""
    return list(
        SubscriberNote.objects
        .filter(subscriber=subscriber, is_active=True)
        .order_by('-created_at')[:MAX_ACTIVE_NOTES]
    )


def update_note(subscriber, note_id: int, content: str = None, is_active: bool = None) -> dict:
    """Update a subscriber note's content or active status."""
    try:
        note = SubscriberNote.objects.get(id=note_id, subscriber=subscriber)
    except SubscriberNote.DoesNotExist:
        return {"error": "Note not found"}

    update_fields = ['updated_at']
    if content is not None:
        note.content = content
        update_fields.append('content')
    if is_active is not None:
        note.is_active = is_active
        update_fields.append('is_active')

    note.save(update_fields=update_fields)

    return {
        "note_id": note.id,
        "category": note.category,
        "content": note.content,
        "is_active": note.is_active,
        "status": "updated",
    }


def format_notes_for_prompt(subscriber) -> str:
    """
    Format active notes as a system prompt block.

    Returns empty string if no notes exist.
    """
    notes = get_active_notes(subscriber)
    if not notes:
        return ""

    lines = ["## What You Know About This User (Long-term Memory)"]
    for note in notes:
        lines.append(f"- [{note.category}] {note.content}")
    lines.append(
        "\nUse this context to personalize responses. "
        "If the user corrects a fact, call update_note to fix or deactivate it."
    )
    return "\n".join(lines)

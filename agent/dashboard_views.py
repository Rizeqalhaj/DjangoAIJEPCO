"""Dashboard API views for conversation history and subscriber notes."""

from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Subscriber
from agent.models import ConversationSession, SubscriberNote


class ConversationListView(APIView):
    """GET /api/agent/conversations/<subscription_number>/"""

    def get(self, request, subscription_number):
        subscriber = get_object_or_404(
            Subscriber, subscription_number=subscription_number
        )
        sessions = (
            ConversationSession.objects
            .filter(subscriber=subscriber)
            .order_by('-created_at')[:20]
        )
        return Response([
            {
                "session_id": s.id,
                "language": s.language,
                "last_intent": s.last_intent,
                "is_active": s.is_active,
                "turn_count": s.turns.count(),
                "created_at": s.created_at.isoformat(),
                "ended_at": s.ended_at.isoformat() if s.ended_at else None,
            }
            for s in sessions
        ])


class ConversationDetailView(APIView):
    """GET /api/agent/conversations/<subscription_number>/<session_id>/"""

    def get(self, request, subscription_number, session_id):
        subscriber = get_object_or_404(
            Subscriber, subscription_number=subscription_number
        )
        session = get_object_or_404(
            ConversationSession, id=session_id, subscriber=subscriber
        )
        turns = session.turns.order_by('created_at')
        return Response({
            "session_id": session.id,
            "language": session.language,
            "is_active": session.is_active,
            "created_at": session.created_at.isoformat(),
            "turns": [
                {
                    "id": t.id,
                    "user_message": t.user_message,
                    "agent_response": t.agent_response,
                    "intent": t.intent,
                    "tools_called": t.tools_called,
                    "language": t.language,
                    "created_at": t.created_at.isoformat(),
                }
                for t in turns
            ],
        })


class SubscriberNotesView(APIView):
    """GET /api/agent/notes/<subscription_number>/ — list active notes"""

    def get(self, request, subscription_number):
        subscriber = get_object_or_404(
            Subscriber, subscription_number=subscription_number
        )
        notes = (
            SubscriberNote.objects
            .filter(subscriber=subscriber, is_active=True)
            .order_by('-created_at')
        )
        return Response([
            {
                "id": n.id,
                "category": n.category,
                "content": n.content,
                "is_active": n.is_active,
                "created_at": n.created_at.isoformat(),
            }
            for n in notes
        ])


class SubscriberNoteDetailView(APIView):
    """DELETE /api/agent/notes/<subscription_number>/<note_id>/ — deactivate a note"""

    def delete(self, request, subscription_number, note_id):
        subscriber = get_object_or_404(
            Subscriber, subscription_number=subscription_number
        )
        note = get_object_or_404(
            SubscriberNote, id=note_id, subscriber=subscriber
        )
        note.is_active = False
        note.save(update_fields=['is_active', 'updated_at'])
        return Response({"status": "deactivated", "note_id": note.id})

"""Agent API views."""

import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from agent.coach import EnergyDetective

logger = logging.getLogger(__name__)


class AgentChatView(APIView):
    """
    Test endpoint for the agent. Send messages without WhatsApp.

    POST /api/agent/chat/
    Body: {"phone": "+962791000001", "message": "ليش فاتورتي غالية؟"}
    """

    def post(self, request):
        phone = request.data.get("phone")
        message = request.data.get("message")

        if not phone or not message:
            return Response(
                {"error": "phone and message required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            agent = EnergyDetective()
            reply = agent.handle_message(phone, message)
        except Exception as e:
            logger.exception("Agent error for phone=%s", phone)
            return Response(
                {"error": f"Agent error: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({
            "reply": reply,
            "phone": phone,
        })

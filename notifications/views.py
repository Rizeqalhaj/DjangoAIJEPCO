"""API views for triggering notification tasks."""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from notifications.tasks import check_plan_verifications


@api_view(["POST"])
@permission_classes([IsAdminUser])
def trigger_check_plans(request):
    """Trigger plan verification check (admin only). Returns count of verified plans."""
    verified = check_plan_verifications()
    return Response({"verified": verified})

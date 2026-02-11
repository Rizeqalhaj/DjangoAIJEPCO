"""Plans API views — list optimization plans for a subscriber."""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Subscriber
from plans.models import OptimizationPlan


class SubscriberPlansView(APIView):
    """GET /api/plans/<subscription_number>/ — list all plans."""

    permission_classes = [IsAuthenticated]

    def get(self, request, subscription_number):
        try:
            subscriber = Subscriber.objects.get(
                subscription_number=subscription_number
            )
        except Subscriber.DoesNotExist:
            return Response({"error": "Subscriber not found"}, status=404)

        if not request.user.is_staff:
            if not (
                hasattr(request.user, "subscriber_profile")
                and request.user.subscriber_profile == subscriber
            ):
                return Response({"error": "Access denied"}, status=403)

        plans = OptimizationPlan.objects.filter(
            subscriber=subscriber
        ).order_by("-created_at")

        return Response([
            {
                "id": p.id,
                "plan_summary": p.plan_summary,
                "detected_pattern": p.detected_pattern,
                "user_hypothesis": p.user_hypothesis,
                "plan_details": p.plan_details,
                "baseline_daily_kwh": p.baseline_daily_kwh,
                "baseline_peak_kwh": p.baseline_peak_kwh,
                "status": p.status,
                "verify_after_date": (
                    str(p.verify_after_date) if p.verify_after_date else None
                ),
                "verification_result": p.verification_result,
                "created_at": p.created_at.isoformat(),
            }
            for p in plans
        ])

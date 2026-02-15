"""Admin-only API views — subscriber list, detail, system stats."""

from datetime import timedelta

from rest_framework.permissions import IsAdminUser, IsAuthenticated

from core.clock import now as clock_now
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Subscriber
from meter.models import MeterReading
from plans.models import OptimizationPlan


class AdminSubscriberListView(APIView):
    """GET /api/admin/subscribers/ — list all subscribers with summary."""

    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        subscribers = Subscriber.objects.all().select_related("user")
        result = []
        for sub in subscribers:
            last_reading = sub.readings.order_by("-timestamp").first()
            result.append({
                "id": sub.id,
                "subscription_number": sub.subscription_number,
                "name": sub.name,
                "phone_number": sub.phone_number,
                "tariff_category": sub.tariff_category,
                "governorate": sub.governorate,
                "area": sub.area,
                "has_ev": sub.has_ev,
                "has_solar": sub.has_solar,
                "is_verified": sub.is_verified,
                "last_reading_at": (
                    last_reading.timestamp.isoformat() if last_reading else None
                ),
                "created_at": sub.created_at.isoformat(),
            })
        return Response(result)


class AdminSubscriberDetailView(APIView):
    """GET /api/admin/subscribers/<id>/ — single subscriber detail."""

    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, subscriber_id):
        try:
            sub = Subscriber.objects.get(id=subscriber_id)
        except Subscriber.DoesNotExist:
            return Response({"error": "Subscriber not found"}, status=404)

        active_plan = OptimizationPlan.objects.filter(
            subscriber=sub, status__in=["active", "monitoring"]
        ).first()

        return Response({
            "id": sub.id,
            "subscription_number": sub.subscription_number,
            "name": sub.name,
            "phone_number": sub.phone_number,
            "language": sub.language,
            "tariff_category": sub.tariff_category,
            "governorate": sub.governorate,
            "area": sub.area,
            "household_size": sub.household_size,
            "has_ev": sub.has_ev,
            "has_solar": sub.has_solar,
            "home_size_sqm": sub.home_size_sqm,
            "is_verified": sub.is_verified,
            "active_plan": {
                "id": active_plan.id,
                "summary": active_plan.plan_summary,
                "status": active_plan.status,
            } if active_plan else None,
        })


class AdminStatsView(APIView):
    """GET /api/admin/stats/ — system-wide aggregate stats."""

    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        thirty_days_ago = clock_now() - timedelta(days=30)
        return Response({
            "total_subscribers": Subscriber.objects.count(),
            "verified_subscribers": Subscriber.objects.filter(
                is_verified=True
            ).count(),
            "total_readings_30d": MeterReading.objects.filter(
                timestamp__gte=thirty_days_ago
            ).count(),
            "active_plans": OptimizationPlan.objects.filter(
                status__in=["active", "monitoring"]
            ).count(),
            "total_plans": OptimizationPlan.objects.count(),
        })

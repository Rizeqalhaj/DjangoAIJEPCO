"""Meter data API views."""

from datetime import datetime, timedelta

from django.db.models import Q, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Subscriber
from meter.analyzer import MeterAnalyzer


class MeterSummaryView(APIView):
    """GET /api/meter/<subscription_number>/summary/"""

    def get(self, request, subscription_number):
        subscriber = get_object_or_404(
            Subscriber, subscription_number=subscription_number
        )
        analyzer = MeterAnalyzer(subscriber)
        days = int(request.query_params.get('days', 30))
        return Response(analyzer.get_consumption_summary(days=days))


class MeterDailyView(APIView):
    """GET /api/meter/<subscription_number>/daily/<target_date>/"""

    def get(self, request, subscription_number, target_date):
        subscriber = get_object_or_404(
            Subscriber, subscription_number=subscription_number
        )
        try:
            parsed_date = datetime.strptime(target_date, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        analyzer = MeterAnalyzer(subscriber)
        return Response(analyzer.get_daily_summary(parsed_date))


class MeterSpikesView(APIView):
    """GET /api/meter/<subscription_number>/spikes/"""

    def get(self, request, subscription_number):
        subscriber = get_object_or_404(
            Subscriber, subscription_number=subscription_number
        )
        analyzer = MeterAnalyzer(subscriber)
        days = int(request.query_params.get('days', 7))
        threshold = float(request.query_params.get('threshold', 2.0))
        spikes = analyzer.detect_spikes(days=days, threshold_factor=threshold)
        return Response({"spikes": spikes, "count": len(spikes)})


class BillForecastView(APIView):
    """GET /api/meter/<subscription_number>/forecast/"""

    def get(self, request, subscription_number):
        subscriber = get_object_or_404(
            Subscriber, subscription_number=subscription_number
        )
        analyzer = MeterAnalyzer(subscriber)
        return Response(analyzer.get_bill_forecast())


class MeterDailySeriesView(APIView):
    """GET /api/meter/<subscription_number>/daily-series/?days=14"""

    def get(self, request, subscription_number):
        subscriber = get_object_or_404(
            Subscriber, subscription_number=subscription_number
        )
        days = int(request.query_params.get("days", 14))
        start = timezone.now() - timedelta(days=days)
        qs = subscriber.readings.filter(timestamp__gte=start)
        daily = (
            qs.annotate(day=TruncDate("timestamp"))
            .values("day")
            .annotate(
                total_kwh=Sum("kwh"),
                peak_kwh=Sum("kwh", filter=Q(tou_period="peak")),
                off_peak_kwh=Sum("kwh", filter=Q(tou_period="off_peak")),
                partial_peak_kwh=Sum("kwh", filter=Q(tou_period="partial_peak")),
            )
            .order_by("day")
        )
        return Response([
            {
                "date": str(d["day"]),
                "total_kwh": round(d["total_kwh"] or 0, 2),
                "peak_kwh": round(d["peak_kwh"] or 0, 2),
                "off_peak_kwh": round(d["off_peak_kwh"] or 0, 2),
                "partial_peak_kwh": round(d["partial_peak_kwh"] or 0, 2),
            }
            for d in daily
        ])


class MeterHourlyProfileView(APIView):
    """GET /api/meter/<subscription_number>/hourly-profile/?days=14"""

    def get(self, request, subscription_number):
        subscriber = get_object_or_404(
            Subscriber, subscription_number=subscription_number
        )
        days = int(request.query_params.get("days", 14))
        now = timezone.now()
        start = (now - timedelta(days=days)).date()
        end = now.date()
        analyzer = MeterAnalyzer(subscriber)
        return Response(analyzer.get_hourly_profile(start, end))

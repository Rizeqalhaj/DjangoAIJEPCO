"""Meter data API views."""

from datetime import datetime, timedelta

from django.db.models import Q, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404
from rest_framework import status

from core.clock import now as clock_now
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Subscriber
from meter.analyzer import MeterAnalyzer


class MeterSummaryView(APIView):
    """GET /api/meter/<subscription_number>/summary/?days=30
    or  GET /api/meter/<subscription_number>/summary/?start_date=2026-01-01&end_date=2026-01-31
    """

    def get(self, request, subscription_number):
        subscriber = get_object_or_404(
            Subscriber, subscription_number=subscription_number
        )
        analyzer = MeterAnalyzer(subscriber)
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date and end_date:
            try:
                sd = datetime.strptime(start_date, '%Y-%m-%d').date()
                ed = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(analyzer.get_consumption_summary(start_date=sd, end_date=ed))
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
    """GET /api/meter/<subscription_number>/spikes/?days=7
    or  GET /api/meter/<subscription_number>/spikes/?start_date=2026-01-01&end_date=2026-01-31
    """

    def get(self, request, subscription_number):
        subscriber = get_object_or_404(
            Subscriber, subscription_number=subscription_number
        )
        analyzer = MeterAnalyzer(subscriber)
        threshold = float(request.query_params.get('threshold', 1.5))
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date and end_date:
            try:
                sd = datetime.strptime(start_date, '%Y-%m-%d').date()
                ed = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            spikes = analyzer.detect_spikes(threshold_factor=threshold, start_date=sd, end_date=ed)
        else:
            days = int(request.query_params.get('days', 7))
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
    """GET /api/meter/<subscription_number>/daily-series/?days=14
    or  GET /api/meter/<subscription_number>/daily-series/?start_date=2026-01-01&end_date=2026-01-31
    """

    def get(self, request, subscription_number):
        subscriber = get_object_or_404(
            Subscriber, subscription_number=subscription_number
        )
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        if start_date and end_date:
            try:
                sd = datetime.strptime(start_date, '%Y-%m-%d').date()
                ed = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            qs = subscriber.readings.filter(
                timestamp__date__gte=sd,
                timestamp__date__lte=ed,
            )
        else:
            days = int(request.query_params.get("days", 14))
            start = clock_now() - timedelta(days=days)
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
    """GET /api/meter/<subscription_number>/hourly-profile/?days=14
    or  GET /api/meter/<subscription_number>/hourly-profile/?start_date=2026-01-01&end_date=2026-01-31
    """

    def get(self, request, subscription_number):
        subscriber = get_object_or_404(
            Subscriber, subscription_number=subscription_number
        )
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        if start_date and end_date:
            try:
                sd = datetime.strptime(start_date, '%Y-%m-%d').date()
                ed = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            days = int(request.query_params.get("days", 14))
            now = clock_now()
            sd = (now - timedelta(days=days)).date()
            ed = now.date()
        analyzer = MeterAnalyzer(subscriber)
        return Response(analyzer.get_hourly_profile(sd, ed))

"""Meter data API views."""

from datetime import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

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

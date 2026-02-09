"""Tariff API views."""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from tariff.engine import get_tou_period, calculate_residential_bill


class TouCurrentView(APIView):
    """GET /api/tariff/current/"""

    def get(self, request):
        return Response(get_tou_period())


class BillCalculateView(APIView):
    """POST /api/tariff/calculate/"""

    def post(self, request):
        monthly_kwh = request.data.get('monthly_kwh')
        if monthly_kwh is None:
            return Response(
                {"error": "monthly_kwh is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            monthly_kwh = float(monthly_kwh)
        except (TypeError, ValueError):
            return Response(
                {"error": "monthly_kwh must be a number"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if monthly_kwh < 0:
            return Response(
                {"error": "monthly_kwh must be non-negative"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        phase = request.data.get('phase', 'single_phase')
        if phase not in ('single_phase', 'three_phase'):
            return Response(
                {"error": "phase must be 'single_phase' or 'three_phase'"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(calculate_residential_bill(monthly_kwh, phase=phase))

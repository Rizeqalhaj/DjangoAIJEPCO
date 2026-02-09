"""DRF serializers for meter API input validation."""

from rest_framework import serializers


class BillCalculateInputSerializer(serializers.Serializer):
    monthly_kwh = serializers.FloatField(min_value=0)
    phase = serializers.ChoiceField(
        choices=["single_phase", "three_phase"],
        default="single_phase",
    )

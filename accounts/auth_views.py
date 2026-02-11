"""Authentication views — JWT login + user profile."""

from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken


def _serialize_subscriber(sub):
    return {
        "id": sub.id,
        "subscription_number": sub.subscription_number,
        "phone_number": sub.phone_number,
        "name": sub.name,
        "language": sub.language,
        "tariff_category": sub.tariff_category,
        "governorate": sub.governorate,
        "area": sub.area,
        "household_size": sub.household_size,
        "has_ev": sub.has_ev,
        "has_solar": sub.has_solar,
        "home_size_sqm": sub.home_size_sqm,
    }


def _serialize_user(user):
    subscriber_data = None
    if hasattr(user, "subscriber_profile") and user.subscriber_profile:
        subscriber_data = _serialize_subscriber(user.subscriber_profile)
    return {
        "id": user.id,
        "username": user.username,
        "is_staff": user.is_staff,
        "subscriber": subscriber_data,
    }


class LoginView(APIView):
    """POST /api/auth/login/ — returns JWT tokens + user profile."""

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        username = request.data.get("username", "").strip()
        password = request.data.get("password", "")
        if not username or not password:
            return Response(
                {"error": "username and password required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = authenticate(username=username, password=password)
        if not user:
            return Response(
                {"error": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        refresh = RefreshToken.for_user(user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": _serialize_user(user),
        })


class MeView(APIView):
    """GET /api/auth/me/ — current user profile."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(_serialize_user(request.user))

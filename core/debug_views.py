"""Debug API endpoints for time-travel testing. Only available when DEBUG=True."""

from datetime import datetime

from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from core.clock import now, set_override, clear_override, get_override, _original_now

JORDAN_TZ = timezone.get_fixed_timezone(180)  # UTC+3


@api_view(["GET", "POST", "DELETE"])
@permission_classes([AllowAny])
def time_override_view(request):
    """
    GET  — Return current time and whether it's overridden.
    POST — Set time override. Body: {"date": "2026-02-09"} or {"datetime": "2026-02-09T14:30:00"}
    DELETE — Clear the override, return to real time.
    """
    if request.method == "GET":
        override = get_override()
        return Response({
            "current_time": now().isoformat(),
            "is_overridden": override is not None,
            "real_time": _original_now().isoformat(),
        })

    if request.method == "DELETE":
        clear_override()
        return Response({
            "current_time": timezone.now().isoformat(),
            "is_overridden": False,
        })

    # POST
    date_str = request.data.get("date")
    datetime_str = request.data.get("datetime")

    if datetime_str:
        try:
            dt = datetime.fromisoformat(datetime_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=JORDAN_TZ)
        except ValueError:
            return Response({"error": "Invalid datetime format. Use ISO format."}, status=400)
    elif date_str:
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
            dt = datetime.combine(d, datetime.now().time(), tzinfo=JORDAN_TZ)
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)
    else:
        return Response({"error": "Provide 'date' or 'datetime' in request body."}, status=400)

    set_override(dt)
    return Response({
        "current_time": dt.isoformat(),
        "is_overridden": True,
    })

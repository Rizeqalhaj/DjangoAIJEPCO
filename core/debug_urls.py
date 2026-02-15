from django.urls import path
from core.debug_views import time_override_view

urlpatterns = [
    path("time/", time_override_view, name="debug-time"),
]

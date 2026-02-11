from django.urls import path

from accounts.admin_views import (
    AdminStatsView,
    AdminSubscriberDetailView,
    AdminSubscriberListView,
)

urlpatterns = [
    path("subscribers/", AdminSubscriberListView.as_view(), name="admin-subscribers"),
    path(
        "subscribers/<int:subscriber_id>/",
        AdminSubscriberDetailView.as_view(),
        name="admin-subscriber-detail",
    ),
    path("stats/", AdminStatsView.as_view(), name="admin-stats"),
]

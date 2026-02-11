from django.urls import path

from plans.views import SubscriberPlansView

app_name = "plans"

urlpatterns = [
    path(
        "<str:subscription_number>/",
        SubscriberPlansView.as_view(),
        name="subscriber-plans",
    ),
]

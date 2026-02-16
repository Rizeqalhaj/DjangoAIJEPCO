from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


def health_check(request):
    return JsonResponse({"status": "ok", "service": "kahrabaai"})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health_check, name='health-check'),
    path('api/auth/', include('accounts.auth_urls')),
    path('api/admin/', include('accounts.admin_urls')),
    path('api/meter/', include('meter.urls')),
    path('api/tariff/', include('tariff.urls')),
    path('api/agent/', include('agent.urls')),
    path('api/plans/', include('plans.urls')),
    path('api/whatsapp/', include('whatsapp.urls')),
    path('api/notifications/', include('notifications.urls')),
]

# Debug/time-travel endpoints — available in all environments for demo purposes
urlpatterns += [
    path('api/debug/', include('core.debug_urls')),
]

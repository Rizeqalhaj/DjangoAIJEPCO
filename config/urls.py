from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


def health_check(request):
    return JsonResponse({"status": "ok", "service": "kahrabaai"})


def run_seed(request):
    """One-time seed endpoint. Call once then remove."""
    import os
    secret = request.GET.get('key', '')
    if secret != os.environ.get('DJANGO_SECRET_KEY', '')[:8]:
        return JsonResponse({"error": "unauthorized"}, status=403)
    try:
        from django.core.management import call_command
        from django.contrib.auth.models import User
        from accounts.models import Subscriber
        call_command('seed_demo')
        call_command('seed_washer')
        return JsonResponse({
            "status": "seeded",
            "users": User.objects.count(),
            "subscribers": Subscriber.objects.count(),
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health_check, name='health-check'),
    path('api/seed/', run_seed, name='run-seed'),
    path('api/auth/', include('accounts.auth_urls')),
    path('api/admin/', include('accounts.admin_urls')),
    path('api/meter/', include('meter.urls')),
    path('api/tariff/', include('tariff.urls')),
    path('api/agent/', include('agent.urls')),
    path('api/plans/', include('plans.urls')),
    path('api/whatsapp/', include('whatsapp.urls')),
    path('api/notifications/', include('notifications.urls')),
]

if settings.DEBUG:
    urlpatterns += [
        path('api/debug/', include('core.debug_urls')),
    ]

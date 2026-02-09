from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


def health_check(request):
    return JsonResponse({"status": "ok", "service": "kahrabaai"})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health_check, name='health-check'),
    path('api/meter/', include('meter.urls')),
    path('api/tariff/', include('tariff.urls')),
    path('api/agent/', include('agent.urls')),
]

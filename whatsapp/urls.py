from django.urls import path
from whatsapp import webhook

app_name = 'whatsapp'

urlpatterns = [
    path('webhook/', webhook.whatsapp_webhook, name='webhook'),
]

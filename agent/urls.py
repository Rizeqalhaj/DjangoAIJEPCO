from django.urls import path
from . import views

app_name = 'agent'

urlpatterns = [
    path('chat/', views.AgentChatView.as_view(), name='chat'),
]

from django.urls import path
from . import views
from . import dashboard_views

app_name = 'agent'

urlpatterns = [
    path('chat/', views.AgentChatView.as_view(), name='chat'),
    # Conversation history
    path(
        'conversations/<str:subscription_number>/',
        dashboard_views.ConversationListView.as_view(),
        name='conversation-list',
    ),
    path(
        'conversations/<str:subscription_number>/<int:session_id>/',
        dashboard_views.ConversationDetailView.as_view(),
        name='conversation-detail',
    ),
    # Subscriber notes
    path(
        'notes/<str:subscription_number>/',
        dashboard_views.SubscriberNotesView.as_view(),
        name='notes-list',
    ),
    path(
        'notes/<str:subscription_number>/<int:note_id>/',
        dashboard_views.SubscriberNoteDetailView.as_view(),
        name='note-detail',
    ),
]

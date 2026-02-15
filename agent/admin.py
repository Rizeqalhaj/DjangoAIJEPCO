from django.contrib import admin
from agent.models import ConversationSession, ConversationTurn, SubscriberNote


@admin.register(ConversationSession)
class ConversationSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'subscriber', 'language', 'last_intent', 'is_active', 'created_at']
    list_filter = ['is_active', 'language']
    raw_id_fields = ['subscriber']


@admin.register(ConversationTurn)
class ConversationTurnAdmin(admin.ModelAdmin):
    list_display = ['id', 'session', 'intent', 'language', 'created_at']
    list_filter = ['language', 'intent']
    raw_id_fields = ['session']


@admin.register(SubscriberNote)
class SubscriberNoteAdmin(admin.ModelAdmin):
    list_display = ['id', 'subscriber', 'category', 'content_preview', 'is_active', 'created_at']
    list_filter = ['category', 'is_active']
    raw_id_fields = ['subscriber', 'source_turn']

    @admin.display(description='Content')
    def content_preview(self, obj):
        return obj.content[:80] if obj.content else ''

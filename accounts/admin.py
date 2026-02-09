from django.contrib import admin
from .models import Subscriber


@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = [
        'subscription_number', 'name', 'phone_number',
        'tariff_category', 'governorate', 'is_verified', 'created_at'
    ]
    list_filter = ['tariff_category', 'governorate', 'is_verified', 'language']
    search_fields = ['subscription_number', 'phone_number', 'name']
    readonly_fields = ['created_at', 'updated_at']

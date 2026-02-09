from django.contrib import admin
from .models import MeterReading


@admin.register(MeterReading)
class MeterReadingAdmin(admin.ModelAdmin):
    list_display = [
        'subscriber', 'timestamp', 'kwh', 'power_kw',
        'tou_period', 'is_simulated'
    ]
    list_filter = ['tou_period', 'is_simulated']
    search_fields = ['subscriber__subscription_number']
    date_hierarchy = 'timestamp'
    raw_id_fields = ['subscriber']

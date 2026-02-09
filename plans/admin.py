from django.contrib import admin
from .models import OptimizationPlan, PlanCheckpoint


class PlanCheckpointInline(admin.TabularInline):
    model = PlanCheckpoint
    extra = 0
    readonly_fields = ['created_at']


@admin.register(OptimizationPlan)
class OptimizationPlanAdmin(admin.ModelAdmin):
    list_display = [
        'subscriber', 'plan_summary', 'status',
        'verify_after_date', 'created_at'
    ]
    list_filter = ['status']
    search_fields = ['subscriber__subscription_number', 'plan_summary']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['subscriber']
    inlines = [PlanCheckpointInline]


@admin.register(PlanCheckpoint)
class PlanCheckpointAdmin(admin.ModelAdmin):
    list_display = [
        'plan', 'check_date', 'avg_daily_kwh',
        'change_vs_baseline_percent'
    ]
    readonly_fields = ['created_at']

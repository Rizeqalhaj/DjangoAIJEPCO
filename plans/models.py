from django.db import models
from core.models import TimestampedModel


class OptimizationPlan(TimestampedModel):
    """A personalized energy optimization plan."""
    subscriber = models.ForeignKey(
        'accounts.Subscriber',
        on_delete=models.CASCADE,
        related_name='plans'
    )

    detected_pattern = models.TextField(
        help_text="Description of the anomaly/pattern the agent found in meter data"
    )
    detection_data = models.JSONField(
        default=dict,
        help_text="Raw analysis data: spike times, magnitudes, baselines, etc."
    )

    user_hypothesis = models.TextField(
        help_text="What the user thinks is causing the pattern"
    )

    plan_summary = models.TextField(
        help_text="Short summary of the plan"
    )
    plan_details = models.JSONField(
        default=dict,
        help_text="Structured plan with specific actions and expected outcomes"
    )

    baseline_daily_kwh = models.FloatField(
        help_text="Average daily consumption at time of plan creation"
    )
    baseline_peak_kwh = models.FloatField(
        help_text="Average daily peak-period consumption at plan creation"
    )
    baseline_monthly_cost_fils = models.IntegerField(
        help_text="Estimated monthly cost at plan creation"
    )

    status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('monitoring', 'Monitoring'),
            ('verified', 'Verified'),
            ('completed', 'Completed'),
            ('abandoned', 'Abandoned'),
        ],
        default='active'
    )

    verify_after_date = models.DateField(
        help_text="Date when the agent should check results"
    )
    verification_result = models.JSONField(
        null=True, blank=True,
        help_text="Comparison of baseline vs actual after monitoring period"
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Plan for {self.subscriber.subscription_number}: {self.plan_summary[:50]}"


class PlanCheckpoint(TimestampedModel):
    """Periodic progress check on an active plan."""
    plan = models.ForeignKey(
        OptimizationPlan,
        on_delete=models.CASCADE,
        related_name='checkpoints'
    )

    check_date = models.DateField()

    avg_daily_kwh = models.FloatField()
    avg_peak_kwh = models.FloatField()
    avg_offpeak_kwh = models.FloatField()
    estimated_cost_fils_per_day = models.IntegerField()

    change_vs_baseline_percent = models.FloatField(
        help_text="Negative = improvement (less consumption)"
    )

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-check_date']

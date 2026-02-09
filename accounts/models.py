from django.db import models
from core.models import TimestampedModel


class Subscriber(TimestampedModel):
    """A JEPCO electricity subscriber."""

    subscription_number = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text="JEPCO subscription number from electricity bill, e.g., 01-123456-01"
    )
    phone_number = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text="WhatsApp phone in E.164 format: +962791234567"
    )
    name = models.CharField(max_length=100, blank=True)
    language = models.CharField(
        max_length=2,
        choices=[('ar', 'Arabic'), ('en', 'English')],
        default='ar'
    )

    tariff_category = models.CharField(
        max_length=30,
        choices=[
            ('residential', 'Residential'),
            ('commercial', 'Commercial'),
            ('agricultural', 'Agricultural'),
            ('ev_home', 'EV Home Charging'),
        ],
        default='residential'
    )
    governorate = models.CharField(
        max_length=50,
        default='Amman',
        help_text="JEPCO service area: Amman, Zarqa, Madaba, or Balqa"
    )
    area = models.CharField(
        max_length=100,
        blank=True,
        help_text="Neighborhood, e.g., Abdoun, Sweifieh, Jubeiha"
    )

    household_size = models.IntegerField(null=True, blank=True)
    has_ev = models.BooleanField(default=False)
    has_solar = models.BooleanField(default=False)
    home_size_sqm = models.IntegerField(null=True, blank=True, help_text="Approximate home size")

    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)

    wants_weekly_report = models.BooleanField(default=True)
    wants_spike_alerts = models.BooleanField(default=True)
    wants_plan_checkups = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name or 'Unknown'} ({self.subscription_number})"

    class Meta:
        ordering = ['-created_at']

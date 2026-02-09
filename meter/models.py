from django.db import models


class MeterReading(models.Model):
    """
    Smart meter interval reading. One row per 15-minute interval.
    Stored in a TimescaleDB hypertable for efficient time-series queries.
    """
    subscriber = models.ForeignKey(
        'accounts.Subscriber',
        on_delete=models.CASCADE,
        related_name='readings'
    )
    timestamp = models.DateTimeField(db_index=True)

    kwh = models.FloatField(help_text="Energy consumed in this interval (kWh)")

    voltage = models.FloatField(null=True, blank=True, help_text="Voltage in volts")
    current_amps = models.FloatField(null=True, blank=True)
    power_factor = models.FloatField(null=True, blank=True)

    power_kw = models.FloatField(
        help_text="Average power draw in kW for this interval (kwh * 4 for 15-min intervals)"
    )
    tou_period = models.CharField(
        max_length=20,
        choices=[
            ('off_peak', 'Off-Peak'),
            ('partial_peak', 'Partial Peak'),
            ('peak', 'Peak'),
        ]
    )

    is_simulated = models.BooleanField(default=True, help_text="True = synthetic demo data")

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['subscriber', 'timestamp']),
            models.Index(fields=['subscriber', 'tou_period', 'timestamp']),
        ]
        unique_together = ['subscriber', 'timestamp']

    def __str__(self):
        return f"{self.subscriber.subscription_number} | {self.timestamp} | {self.kwh} kWh"

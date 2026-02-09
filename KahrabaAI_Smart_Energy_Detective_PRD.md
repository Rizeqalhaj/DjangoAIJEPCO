# KahrabaAI — Smart Energy Detective (محقق الطاقة الذكي)
# Product Requirements Document (PRD)

> **For:** Claude Code (AI coding agent)  
> **How to use:** Build this project ONE PHASE AT A TIME. Complete each phase fully, test it, then move to the next. Do NOT read ahead and try to build everything at once. Each phase is self-contained and builds on the previous one.

---

## TABLE OF CONTENTS

1. [Project Overview](#1-project-overview)
2. [Tech Stack](#2-tech-stack)
3. [Project Structure](#3-project-structure)
4. [PHASE 1: Foundation](#phase-1-foundation-hours-1-3)
5. [PHASE 2: Smart Meter Data Layer](#phase-2-smart-meter-data-layer-hours-3-5)
6. [PHASE 3: AI Agent Core](#phase-3-ai-agent-core-hours-5-8)
7. [PHASE 4: WhatsApp Integration](#phase-4-whatsapp-integration-hours-8-10)
8. [PHASE 5: Investigation & Plan Engine](#phase-5-investigation--plan-engine-hours-10-13)
9. [PHASE 6: Polish & Demo](#phase-6-polish--demo-hours-13-15)
10. [Appendix: Seed Data Profiles](#appendix-a-seed-data-profiles)
11. [Appendix: TOU Tariff Reference](#appendix-b-tou-tariff-reference)
12. [Appendix: Arabic Message Templates](#appendix-c-arabic-message-templates)

---

## 1. Project Overview

### What Is This?

KahrabaAI is a WhatsApp AI agent that acts as a **personal energy detective** for JEPCO electricity subscribers in Jordan. It reads their smart meter data, detects unusual consumption patterns, collaborates with the user to figure out what's causing them, creates a personalized optimization plan, and then verifies whether the plan worked using the same meter data.

### The Core Loop

```
DETECT → INVESTIGATE → PLAN → VERIFY → REPEAT
```

1. **DETECT:** Agent analyzes 15-min interval smart meter data. Finds spikes, trends, anomalies.
2. **INVESTIGATE:** Agent does NOT guess the cause. It tells the user what it sees and ASKS what might be causing it. The user provides context (e.g., "I turn on AC when I get home at 5").
3. **PLAN:** Agent creates a concrete, actionable plan based on the user's input + TOU tariff data (e.g., "Pre-cool your home at 2 PM when electricity is cheapest").
4. **VERIFY:** After 1-2 weeks, agent checks the meter data again. Did the spike shrink? Did the bill improve? Reports back with proof.

### Key Design Principle

**The AI is honest.** It never says "your AC is using too much power" because it cannot know that from meter data alone. It says "I see a 3 kW spike every day at 5 PM — what do you think is causing this?" The human provides the domain knowledge about their own home. The AI provides the data analysis, tariff optimization, and follow-up verification.

### Target User

A JEPCO residential subscriber who:
- Gets a monthly electricity bill they don't understand
- Doesn't know when electricity is cheap vs expensive (TOU periods)
- Wants to reduce their bill but doesn't know where to start
- Uses WhatsApp daily (90%+ of Jordanians)

---

## 2. Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Language | Python 3.11+ | Django ecosystem, ML libraries |
| Framework | Django 5.x + DRF | Rapid development, ORM, admin |
| Database | PostgreSQL 16 | Reliable, JSON support |
| Time-series | TimescaleDB extension | Efficient interval data queries |
| Cache | Redis 7.x | Conversation state, rate limiting |
| Task Queue | Celery + Redis | Async message processing, scheduled tasks |
| LLM (reasoning) | Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`) | Main agent reasoning, plan generation |
| LLM (fast tasks) | Claude Haiku 4.5 (`claude-haiku-4-5-20251001`) | Intent classification, language detection |
| Vector DB | ChromaDB | RAG for tariff docs and FAQs |
| Embeddings | `intfloat/multilingual-e5-large` | Arabic + English support |
| WhatsApp | Meta WhatsApp Business Cloud API v21.0 | Message send/receive |
| Containerization | Docker + Docker Compose | Local dev environment |

---

## 3. Project Structure

```
kahrabaai/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── manage.py
├── .env.example
│
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── celery.py
│   └── wsgi.py
│
├── core/                        # Shared utilities
│   ├── __init__.py
│   ├── models.py                # TimestampedModel base class
│   ├── exceptions.py
│   └── utils.py
│
├── accounts/                    # User management
│   ├── __init__.py
│   ├── models.py                # Subscriber model
│   ├── serializers.py
│   ├── services.py              # Registration, verification
│   ├── views.py
│   └── admin.py
│
├── meter/                       # Smart meter data layer
│   ├── __init__.py
│   ├── models.py                # MeterReading model (TimescaleDB)
│   ├── services.py              # Data query interface (abstraction layer)
│   ├── analyzer.py              # Spike detection, trend analysis, anomaly detection
│   ├── generator.py             # Synthetic data generator for demo
│   ├── serializers.py
│   ├── views.py
│   └── management/
│       └── commands/
│           └── generate_meter_data.py
│
├── tariff/                      # TOU tariff engine
│   ├── __init__.py
│   ├── engine.py                # Rate calculation, period detection
│   ├── optimizer.py             # Cost optimization recommendations
│   └── views.py
│
├── agent/                       # AI agent
│   ├── __init__.py
│   ├── coach.py                 # Main EnergyDetective agent
│   ├── intent.py                # Intent classifier (Haiku)
│   ├── tools.py                 # Agent tool definitions + implementations
│   ├── conversation.py          # Redis conversation state manager
│   └── prompts.py               # System prompt, response guidelines
│
├── plans/                       # Optimization plans
│   ├── __init__.py
│   ├── models.py                # OptimizationPlan, PlanCheckpoint models
│   ├── services.py              # Plan creation, progress tracking, verification
│   ├── serializers.py
│   └── views.py
│
├── whatsapp/                    # WhatsApp integration
│   ├── __init__.py
│   ├── webhook.py               # Incoming message handler
│   ├── sender.py                # Outgoing message sender
│   ├── signature.py             # Webhook signature verification
│   └── tasks.py                 # Celery tasks for async processing
│
├── rag/                         # Knowledge base
│   ├── __init__.py
│   ├── ingest.py                # Document ingestion
│   ├── retriever.py             # Search interface
│   └── documents/
│       ├── tou_tariffs.md
│       ├── billing_faq_ar.md
│       ├── billing_faq_en.md
│       ├── energy_saving_tips.md
│       └── jepco_tariff_tiers.md
│
├── notifications/               # Scheduled alerts
│   ├── __init__.py
│   ├── tasks.py                 # Celery periodic tasks
│   └── templates.py             # Message templates
│
├── seed/                        # Demo data
│   └── management/
│       └── commands/
│           └── seed_demo.py     # Creates demo subscribers + meter data
│
└── tests/
    ├── test_tariff_engine.py
    ├── test_meter_analyzer.py
    ├── test_plan_service.py
    ├── test_intent_classifier.py
    └── test_webhook.py
```

---

# BUILD PHASES

Each phase is designed to be completed independently. After each phase, you should be able to run the project and verify that the phase works correctly before moving on.

---

## PHASE 1: Foundation (Hours 1-3)

**Goal:** Django project running with database, models, Docker, and basic API health check.

### Phase 1 Deliverables
- [ ] Django project scaffolded with all apps created
- [ ] Docker Compose running PostgreSQL + TimescaleDB + Redis
- [ ] All database models created and migrated
- [ ] Django admin registered for all models
- [ ] Health check endpoint returns 200
- [ ] All environment variables documented

### 1A. Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  db:
    image: timescale/timescaledb:latest-pg16
    environment:
      POSTGRES_DB: kahrabaai
      POSTGRES_USER: kahrabaai
      POSTGRES_PASSWORD: kahrabaai_dev
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

Note: The Django app, Celery worker, and Celery beat run directly on the host during development (not in Docker). Only PostgreSQL and Redis run in containers.

### 1B. Environment Variables

```bash
# .env.example

# Django
DJANGO_SECRET_KEY=change-me-to-a-random-string
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Database (matches docker-compose)
DATABASE_URL=postgres://kahrabaai:kahrabaai_dev@localhost:5432/kahrabaai

# Redis
REDIS_URL=redis://localhost:6379/0

# Anthropic
ANTHROPIC_API_KEY=sk-ant-your-key-here

# WhatsApp (fill in later in Phase 4)
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_VERIFY_TOKEN=kahrabaai-verify-token
WHATSAPP_APP_SECRET=

# ChromaDB
CHROMA_PERSIST_DIR=./chroma_data
```

### 1C. Base Model

```python
# core/models.py
from django.db import models

class TimestampedModel(models.Model):
    """Abstract base model with created/updated timestamps."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
```

### 1D. Subscriber Model

This is the main user model. Users are identified by their JEPCO subscription number and linked via WhatsApp phone number.

```python
# accounts/models.py
from django.db import models
from core.models import TimestampedModel

class Subscriber(TimestampedModel):
    """A JEPCO electricity subscriber."""

    # Identity
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

    # Account details
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

    # Household context (user-provided, helps agent give better advice)
    household_size = models.IntegerField(null=True, blank=True)
    has_ev = models.BooleanField(default=False)
    has_solar = models.BooleanField(default=False)
    home_size_sqm = models.IntegerField(null=True, blank=True, help_text="Approximate home size")

    # Registration state
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)

    # Notification preferences
    wants_weekly_report = models.BooleanField(default=True)
    wants_spike_alerts = models.BooleanField(default=True)
    wants_plan_checkups = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name or 'Unknown'} ({self.subscription_number})"

    class Meta:
        ordering = ['-created_at']
```

### 1E. Meter Reading Model

This is the core data model. Each row is one 15-minute interval reading from the smart meter.

```python
# meter/models.py
from django.db import models
from core.models import TimestampedModel

class MeterReading(models.Model):
    """
    Smart meter interval reading. One row per 15-minute interval.
    
    This is the primary data source for the entire application.
    In production: populated by JEPCO's Itron MDM API.
    In demo: populated by the synthetic data generator.
    
    Stored in a TimescaleDB hypertable for efficient time-series queries.
    """
    subscriber = models.ForeignKey(
        'accounts.Subscriber',
        on_delete=models.CASCADE,
        related_name='readings'
    )
    timestamp = models.DateTimeField(db_index=True)
    
    # Core measurement
    kwh = models.FloatField(help_text="Energy consumed in this interval (kWh)")
    
    # Power quality (available from Itron meters)
    voltage = models.FloatField(null=True, blank=True, help_text="Voltage in volts")
    current_amps = models.FloatField(null=True, blank=True)
    power_factor = models.FloatField(null=True, blank=True)
    
    # Derived fields (computed on insert for fast queries)
    power_kw = models.FloatField(
        help_text="Average power draw in kW for this interval (kwh * 4 for 15-min intervals)"
    )
    tou_period = models.CharField(
        max_length=20,
        choices=[
            ('off_peak', 'Off-Peak'),        # 05:00 - 14:00
            ('partial_peak', 'Partial Peak'), # 14:00 - 17:00 and 23:00 - 05:00
            ('peak', 'Peak'),                 # 17:00 - 23:00
        ]
    )
    
    # Flags
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
```

**IMPORTANT:** After migration, convert this to a TimescaleDB hypertable:

```python
# In a migration or post-migrate signal:
from django.db import connection

def create_hypertable(apps, schema_editor):
    with connection.cursor() as cursor:
        cursor.execute("SELECT create_hypertable('meter_meterreading', 'timestamp', if_not_exists => TRUE);")
```

### 1F. Optimization Plan Models

```python
# plans/models.py
from django.db import models
from core.models import TimestampedModel

class OptimizationPlan(TimestampedModel):
    """
    A personalized energy optimization plan created collaboratively
    between the AI agent and the subscriber.
    """
    subscriber = models.ForeignKey(
        'accounts.Subscriber',
        on_delete=models.CASCADE,
        related_name='plans'
    )

    # What the agent detected
    detected_pattern = models.TextField(
        help_text="Description of the anomaly/pattern the agent found in meter data"
    )
    detection_data = models.JSONField(
        default=dict,
        help_text="Raw analysis data: spike times, magnitudes, baselines, etc."
    )

    # What the user said is causing it
    user_hypothesis = models.TextField(
        help_text="What the user thinks is causing the pattern, e.g., 'AC when I get home'"
    )

    # The plan
    plan_summary = models.TextField(
        help_text="Short summary of the plan, e.g., 'Shift AC pre-cooling to 2 PM off-peak'"
    )
    plan_details = models.JSONField(
        default=dict,
        help_text="Structured plan with specific actions and expected outcomes"
    )
    # plan_details example:
    # {
    #     "actions": [
    #         {
    #             "action": "Pre-cool home at 2 PM instead of 5 PM",
    #             "expected_impact_kwh": 3.0,
    #             "expected_savings_fils_per_day": 156,
    #             "tou_benefit": "Moves 3 kWh from peak (160 fils) to off-peak (108 fils)"
    #         }
    #     ],
    #     "monitoring_period_days": 7,
    #     "baseline_peak_kwh_avg": 12.5,
    #     "target_peak_kwh_avg": 9.5,
    #     "estimated_monthly_savings_jod": 4.68
    # }

    # Baseline snapshot (meter data summary at plan creation time)
    baseline_daily_kwh = models.FloatField(
        help_text="Average daily consumption at time of plan creation"
    )
    baseline_peak_kwh = models.FloatField(
        help_text="Average daily peak-period consumption at plan creation"
    )
    baseline_monthly_cost_fils = models.IntegerField(
        help_text="Estimated monthly cost at plan creation"
    )

    # Plan lifecycle
    status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),           # Plan is being followed
            ('monitoring', 'Monitoring'),     # Waiting for verification period
            ('verified', 'Verified'),         # Results checked
            ('completed', 'Completed'),       # Plan achieved its goal
            ('abandoned', 'Abandoned'),       # User stopped following plan
        ],
        default='active'
    )

    # Verification
    verify_after_date = models.DateField(
        help_text="Date when the agent should check results (plan creation + monitoring period)"
    )
    verification_result = models.JSONField(
        null=True, blank=True,
        help_text="Comparison of baseline vs actual after monitoring period"
    )
    # verification_result example:
    # {
    #     "period_analyzed": "2026-02-01 to 2026-02-07",
    #     "baseline_peak_kwh_avg": 12.5,
    #     "actual_peak_kwh_avg": 9.8,
    #     "reduction_kwh": 2.7,
    #     "reduction_percent": 21.6,
    #     "actual_savings_fils_per_day": 140,
    #     "plan_worked": true,
    #     "summary_ar": "استهلاكك وقت الذروة نزل 21.6%! وفرت تقريباً 4.2 دينار هالأسبوع",
    #     "summary_en": "Your peak consumption dropped 21.6%! You saved approximately JOD 4.2 this week"
    # }

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Plan for {self.subscriber.subscription_number}: {self.plan_summary[:50]}"


class PlanCheckpoint(TimestampedModel):
    """
    Periodic progress check on an active plan.
    The agent creates these when checking in with the user.
    """
    plan = models.ForeignKey(
        OptimizationPlan,
        on_delete=models.CASCADE,
        related_name='checkpoints'
    )

    check_date = models.DateField()
    
    # Meter data snapshot at this checkpoint
    avg_daily_kwh = models.FloatField()
    avg_peak_kwh = models.FloatField()
    avg_offpeak_kwh = models.FloatField()
    estimated_cost_fils_per_day = models.IntegerField()

    # Comparison to baseline
    change_vs_baseline_percent = models.FloatField(
        help_text="Negative = improvement (less consumption)"
    )

    # Agent's assessment
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-check_date']
```

### 1G. URL Configuration

```python
# config/urls.py
from django.contrib import admin
from django.urls import path
from django.http import JsonResponse

def health_check(request):
    return JsonResponse({"status": "ok", "service": "kahrabaai"})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health_check, name='health-check'),
    # More URLs added in later phases
]
```

### 1H. Requirements

```
# requirements.txt
django>=5.0,<6.0
djangorestframework>=3.15
django-environ
psycopg2-binary
redis
celery[redis]
httpx
anthropic>=0.40.0
chromadb
sentence-transformers
numpy
pandas
gunicorn
```

### Phase 1 Verification

After completing Phase 1, verify:
```bash
# 1. Start containers
docker-compose up -d

# 2. Install deps
pip install -r requirements.txt

# 3. Run migrations
python manage.py migrate

# 4. Create superuser
python manage.py createsuperuser

# 5. Start server
python manage.py runserver

# 6. Test health check
curl http://localhost:8000/api/health/
# Should return: {"status": "ok", "service": "kahrabaai"}

# 7. Test admin
# Open http://localhost:8000/admin/ — should see Subscriber, MeterReading, OptimizationPlan models
```

---

## PHASE 2: Smart Meter Data Layer (Hours 3-5)

**Goal:** Synthetic meter data generator + data analysis service that can detect spikes, trends, and anomalies.

### Phase 2 Deliverables
- [ ] Synthetic meter data generator creates realistic 90-day data for demo users
- [ ] `seed_demo` management command creates subscribers + their meter data
- [ ] Meter analyzer service detects daily spikes, weekly trends, month-over-month changes
- [ ] TOU tariff engine returns correct rates for any timestamp
- [ ] API endpoints for meter data queries work

### 2A. TOU Tariff Engine

```python
# tariff/engine.py

from datetime import datetime, time, date
from zoneinfo import ZoneInfo
from typing import Optional

JORDAN_TZ = ZoneInfo("Asia/Amman")

# ─── EMRC TOU Rates (effective July 2025) ───
# Source: Energy and Minerals Regulatory Commission
# All values in fils per kWh (1 JOD = 1000 fils)

TOU_RATES = {
    "ev_home": {
        "off_peak": 108,
        "partial_peak": 118,
        "peak": 160,
    },
    "ev_public": {
        "off_peak": 103,
        "partial_peak": 113,
        "peak": 133,
    },
}

# ─── JEPCO Residential Tariff (Tiered / Block) ───
# This is the standard residential tariff, NOT TOU.
# Most residential subscribers are still on this tariff.
# Tiers are based on monthly kWh consumption.

RESIDENTIAL_TIERS = [
    # (max_kwh_in_tier, fils_per_kwh)
    (160, 33),      # First 160 kWh: 33 fils
    (160, 72),      # Next 160 kWh (161-320): 72 fils
    (160, 86),      # Next 160 kWh (321-480): 86 fils
    (160, 114),     # Next 160 kWh (481-640): 114 fils
    (160, 158),     # Next 160 kWh (641-800): 158 fils
    (200, 200),     # Next 200 kWh (801-1000): 200 fils
    (float('inf'), 265),  # Above 1000 kWh: 265 fils
]

# Monthly fixed charges (fils)
RESIDENTIAL_FIXED_CHARGE_FILS = {
    "single_phase": 500,   # 0.5 JOD/month
    "three_phase": 1500,   # 1.5 JOD/month
}


def get_tou_period(dt: Optional[datetime] = None) -> dict:
    """
    Determine the TOU period for a given datetime.

    TOU Periods (Jordan):
        Off-Peak:      05:00 - 14:00  (cheapest — aligned with solar generation)
        Partial Peak:  14:00 - 17:00  AND  23:00 - 05:00
        Peak:          17:00 - 23:00  (most expensive — evening demand)

    Returns dict with:
        period: str ("off_peak", "partial_peak", "peak")
        period_name_ar: str
        period_name_en: str
        start_time: str (HH:MM)
        end_time: str (HH:MM)
        minutes_remaining: int (minutes until period ends)
        next_period: str
    """
    if dt is None:
        dt = datetime.now(JORDAN_TZ)
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=JORDAN_TZ)

    hour = dt.hour
    minute = dt.minute

    if 5 <= hour < 14:
        period = "off_peak"
        start, end = "05:00", "14:00"
        mins_left = (14 - hour) * 60 - minute
        next_p = "partial_peak"
    elif 14 <= hour < 17:
        period = "partial_peak"
        start, end = "14:00", "17:00"
        mins_left = (17 - hour) * 60 - minute
        next_p = "peak"
    elif 17 <= hour < 23:
        period = "peak"
        start, end = "17:00", "23:00"
        mins_left = (23 - hour) * 60 - minute
        next_p = "partial_peak"
    else:  # 23 <= hour or hour < 5
        period = "partial_peak"
        start, end = "23:00", "05:00"
        if hour >= 23:
            mins_left = (24 - hour + 5) * 60 - minute
        else:
            mins_left = (5 - hour) * 60 - minute
        next_p = "off_peak"

    names = {
        "off_peak":      {"ar": "خارج الذروة", "en": "Off-Peak"},
        "partial_peak":  {"ar": "ذروة جزئية",  "en": "Partial Peak"},
        "peak":          {"ar": "وقت الذروة",  "en": "Peak"},
    }

    return {
        "period": period,
        "period_name_ar": names[period]["ar"],
        "period_name_en": names[period]["en"],
        "start_time": start,
        "end_time": end,
        "minutes_remaining": max(0, mins_left),
        "next_period": next_p,
        "next_period_name_ar": names[next_p]["ar"],
        "next_period_name_en": names[next_p]["en"],
    }


def calculate_residential_bill(monthly_kwh: float, phase: str = "single_phase") -> dict:
    """
    Calculate a residential electricity bill using JEPCO's tiered tariff.

    Args:
        monthly_kwh: Total monthly consumption in kWh
        phase: "single_phase" or "three_phase"

    Returns:
        {
            "total_fils": int,
            "total_jod": float,
            "fixed_charge_fils": int,
            "energy_charge_fils": int,
            "tier_breakdown": [
                {"tier": 1, "kwh": 160, "rate_fils": 33, "cost_fils": 5280},
                ...
            ],
            "avg_rate_fils": float,  # effective average rate
        }
    """
    remaining = monthly_kwh
    tier_breakdown = []
    total_energy = 0

    for i, (tier_kwh, rate) in enumerate(RESIDENTIAL_TIERS):
        used_in_tier = min(remaining, tier_kwh)
        if used_in_tier <= 0:
            break
        cost = int(used_in_tier * rate)
        tier_breakdown.append({
            "tier": i + 1,
            "kwh": round(used_in_tier, 1),
            "rate_fils": rate,
            "cost_fils": cost,
        })
        total_energy += cost
        remaining -= used_in_tier

    fixed = RESIDENTIAL_FIXED_CHARGE_FILS.get(phase, 500)
    total = total_energy + fixed

    return {
        "total_fils": total,
        "total_jod": round(total / 1000, 2),
        "fixed_charge_fils": fixed,
        "energy_charge_fils": total_energy,
        "tier_breakdown": tier_breakdown,
        "avg_rate_fils": round(total_energy / monthly_kwh, 1) if monthly_kwh > 0 else 0,
        "monthly_kwh": round(monthly_kwh, 1),
    }


def estimate_cost_by_period(kwh_by_period: dict, tariff_type: str = "residential") -> dict:
    """
    Estimate cost breakdown by TOU period.
    
    For residential subscribers (NOT on TOU tariff), this shows what they
    WOULD save if they shifted consumption. They pay tiered rates, but the
    TOU comparison shows the value of shifting.

    Args:
        kwh_by_period: {"off_peak": 150, "partial_peak": 80, "peak": 120}
        tariff_type: "residential" or "ev_home"

    Returns:
        {
            "total_kwh": 350,
            "cost_at_current_pattern": {...},
            "cost_if_shifted_to_offpeak": {...},
            "potential_savings_jod": 5.2,
        }
    """
    pass  # Implement: compare current pattern vs all-offpeak scenario
```

### 2B. Synthetic Meter Data Generator

This generates realistic consumption data for demo subscribers. Each subscriber gets a distinct "personality" that creates recognizable patterns for the agent to detect.

```python
# meter/generator.py

import numpy as np
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

JORDAN_TZ = ZoneInfo("Asia/Amman")

# ─── Subscriber Profiles for Demo Data ───
# Each profile defines consumption patterns that create
# specific anomalies for the agent to detect.

PROFILES = {
    "ev_peak_charger": {
        # Problem: Charges EV every evening at 7 PM during peak
        # Pattern: 7 kW block from 19:00-23:00 most weekdays
        "description": "EV owner who charges at peak every evening",
        "base_load_kw": 0.4,
        "patterns": [
            {"name": "morning_routine", "hours": (6, 8), "add_kw": 1.5, "variance": 0.3},
            {"name": "evening_cooking", "hours": (17, 19), "add_kw": 2.0, "variance": 0.5},
            {"name": "ev_charging", "hours": (19, 23), "add_kw": 7.0, "variance": 0.5, "weekday_only": True, "probability": 0.8},
            {"name": "evening_lights_tv", "hours": (18, 23), "add_kw": 1.0, "variance": 0.3},
        ],
    },
    "ac_heavy_summer": {
        # Problem: AC runs all afternoon/evening in summer, bill doubles
        # Pattern: 3-4 kW from 14:00-23:00 in summer months
        "description": "Heavy AC user, bill shock in summer",
        "base_load_kw": 0.5,
        "patterns": [
            {"name": "morning_routine", "hours": (6, 8), "add_kw": 1.2, "variance": 0.3},
            {"name": "ac_afternoon", "hours": (14, 18), "add_kw": 3.5, "variance": 0.8, "summer_only": True},
            {"name": "ac_evening", "hours": (18, 23), "add_kw": 3.0, "variance": 0.7, "summer_only": True},
            {"name": "evening_normal", "hours": (18, 22), "add_kw": 1.5, "variance": 0.4},
        ],
    },
    "water_heater_peak": {
        # Problem: Electric water heater runs during peak every evening
        # Pattern: 2.5 kW spike from 18:00-19:30 daily
        "description": "Water heater at peak time — easy fix, big savings",
        "base_load_kw": 0.35,
        "patterns": [
            {"name": "morning_routine", "hours": (6, 8), "add_kw": 1.0, "variance": 0.2},
            {"name": "water_heater_evening", "hours": (18, 20), "add_kw": 2.5, "variance": 0.3, "probability": 0.9},
            {"name": "evening_normal", "hours": (18, 22), "add_kw": 1.2, "variance": 0.3},
        ],
    },
    "baseline_creep": {
        # Problem: Consumption slowly rising over 3 months (new appliance? degrading insulation?)
        # Pattern: Each month is ~10% higher than the last
        "description": "Slowly increasing consumption over months",
        "base_load_kw": 0.4,
        "monthly_increase_percent": 10,
        "patterns": [
            {"name": "morning_routine", "hours": (6, 8), "add_kw": 1.3, "variance": 0.3},
            {"name": "daytime_home", "hours": (10, 16), "add_kw": 0.8, "variance": 0.4},
            {"name": "evening_normal", "hours": (17, 22), "add_kw": 2.0, "variance": 0.5},
        ],
    },
    "efficient_user": {
        # This is the "good" example — mostly off-peak consumption
        # Pattern: Low peak usage, charges EV at night
        "description": "Energy-conscious user, mostly off-peak",
        "base_load_kw": 0.3,
        "patterns": [
            {"name": "morning_routine", "hours": (6, 8), "add_kw": 1.0, "variance": 0.2},
            {"name": "daytime_laundry", "hours": (9, 12), "add_kw": 1.5, "variance": 0.5, "probability": 0.3},
            {"name": "evening_light", "hours": (18, 22), "add_kw": 1.0, "variance": 0.3},
            {"name": "ev_night_charge", "hours": (1, 5), "add_kw": 7.0, "variance": 0.3, "probability": 0.6},
        ],
    },
}


def generate_meter_data(subscriber, profile_name: str, days: int = 90) -> list:
    """
    Generate synthetic 15-minute interval meter data for a subscriber.

    Args:
        subscriber: Subscriber model instance
        profile_name: Key from PROFILES dict
        days: Number of days of historical data to generate

    Returns:
        List of MeterReading instances (not yet saved to DB).
        Call MeterReading.objects.bulk_create() on the result.

    Implementation notes:
        - Generate data from (today - days) to today
        - 96 readings per day (24 hours * 4 intervals per hour)
        - Apply profile patterns to create realistic consumption curves
        - Add random noise (normal distribution) for realism
        - For "summer_only" patterns: apply only if month is 6-9
        - For "weekday_only" patterns: apply only if day is Mon-Fri
        - For "probability" patterns: apply with given probability per day
        - For "baseline_creep": multiply all patterns by (1 + monthly_increase_percent/100)^month_offset
        - Compute power_kw = kwh * 4 (since 15-min interval, kWh * 4 = average kW)
        - Compute tou_period using tariff.engine.get_tou_period(timestamp)
        - Never generate negative kWh — clamp to 0
    """
    pass  # IMPLEMENT THIS
```

### 2C. Meter Data Analyzer

This is the "detective" brain — it looks at meter data and finds interesting patterns.

```python
# meter/analyzer.py

from datetime import datetime, timedelta, date
from typing import Optional
from django.db.models import Avg, Sum, Max, Min, F, Q
from django.db.models.functions import TruncHour, TruncDate, ExtractHour

class MeterAnalyzer:
    """
    Analyzes smart meter data to find patterns, spikes, and anomalies.
    
    All methods return plain dicts — no AI interpretation.
    The AI agent uses these results to have a conversation with the user.
    """

    def __init__(self, subscriber):
        self.subscriber = subscriber
        self.readings = subscriber.readings  # Related manager

    def get_daily_summary(self, target_date: date) -> dict:
        """
        Summarize a single day's consumption.

        Returns:
            {
                "date": "2026-02-06",
                "total_kwh": 28.5,
                "peak_kwh": 12.3,        # 17:00-23:00
                "off_peak_kwh": 10.2,     # 05:00-14:00
                "partial_peak_kwh": 6.0,  # rest
                "max_power_kw": 8.5,      # highest single interval
                "max_power_hour": 19,     # hour of max power (0-23)
                "estimated_cost_fils": 2850,
                "cost_breakdown_by_period": {
                    "peak": {"kwh": 12.3, "cost_fils": ...},
                    "off_peak": {"kwh": 10.2, "cost_fils": ...},
                    "partial_peak": {"kwh": 6.0, "cost_fils": ...},
                },
            }
        """
        pass  # IMPLEMENT: query readings for target_date, aggregate by TOU period

    def get_hourly_profile(self, start_date: date, end_date: date) -> dict:
        """
        Average consumption by hour of day over a date range.
        This creates the "typical day" profile.

        Returns:
            {
                "period": {"start": "2026-01-01", "end": "2026-01-31"},
                "hourly_avg_kw": [0.4, 0.35, 0.3, ..., 1.2, 3.5, 7.8, ...],  # 24 values
                "peak_hour": 19,           # hour with highest average
                "peak_avg_kw": 7.8,
                "lowest_hour": 3,
                "lowest_avg_kw": 0.3,
            }
        """
        pass  # IMPLEMENT: GROUP BY hour, AVG(power_kw)

    def detect_spikes(self, days: int = 7, threshold_factor: float = 2.0) -> list:
        """
        Find unusual consumption spikes in the last N days.
        A spike is an interval where power_kw exceeds (threshold_factor * rolling_average).

        Returns:
            [
                {
                    "timestamp": "2026-02-05T19:15:00",
                    "power_kw": 8.5,
                    "baseline_kw": 2.1,
                    "spike_factor": 4.05,   # how many times above baseline
                    "tou_period": "peak",
                    "duration_minutes": 240, # how long the spike lasted
                    "estimated_extra_cost_fils": 520,
                },
                ...
            ]
        """
        pass  # IMPLEMENT: compare each reading to 30-day same-hour average

    def detect_recurring_pattern(self, days: int = 14) -> list:
        """
        Find patterns that repeat daily or weekly.
        E.g., "Every weekday at 19:00, consumption jumps to 8 kW for 4 hours."

        Returns:
            [
                {
                    "pattern_type": "daily",  # or "weekday", "weekend"
                    "start_hour": 19,
                    "end_hour": 23,
                    "avg_power_kw": 8.2,
                    "occurrences": 10,         # out of 14 days
                    "consistency": 0.71,        # 10/14
                    "estimated_daily_cost_fils": 520,
                    "tou_period": "peak",
                },
                ...
            ]
        """
        pass  # IMPLEMENT: cluster readings by hour, find consistent high-power blocks

    def compare_periods(self, period1_start: date, period1_end: date,
                        period2_start: date, period2_end: date) -> dict:
        """
        Compare two time periods (e.g., this week vs last week, or this month vs last month).

        Returns:
            {
                "period1": {"start": ..., "end": ..., "avg_daily_kwh": 28.5, "avg_cost_fils_per_day": 2850},
                "period2": {"start": ..., "end": ..., "avg_daily_kwh": 22.1, "avg_cost_fils_per_day": 2210},
                "change_kwh": -6.4,
                "change_percent": -22.5,
                "change_cost_fils": -640,
                "change_cost_jod": -0.64,
                "improved": True,
            }
        """
        pass  # IMPLEMENT: aggregate both periods, compute deltas

    def get_bill_forecast(self, days_in_month: int = 30) -> dict:
        """
        Forecast end-of-month bill based on consumption so far this month.

        Returns:
            {
                "days_elapsed": 6,
                "days_remaining": 24,
                "actual_kwh_so_far": 171,
                "projected_monthly_kwh": 855,
                "projected_bill": {
                    "total_fils": 45000,
                    "total_jod": 45.0,
                    "tier_reached": 5,
                    "warning": "You're on track to hit tier 5 (158 fils/kWh). Last month was tier 4."
                },
                "last_month_kwh": 720,
                "last_month_bill_fils": 38000,
                "change_vs_last_month_percent": 18.75,
            }
        """
        pass  # IMPLEMENT: extrapolate from current month's data

    def get_consumption_summary(self, days: int = 30) -> dict:
        """
        High-level consumption summary for the agent to use as context.

        Returns:
            {
                "period_days": 30,
                "total_kwh": 855,
                "avg_daily_kwh": 28.5,
                "avg_daily_cost_fils": 2850,
                "peak_share_percent": 43.2,      # % of total consumed during peak
                "off_peak_share_percent": 35.8,
                "partial_peak_share_percent": 21.0,
                "highest_day": {"date": "2026-02-03", "kwh": 38.2},
                "lowest_day": {"date": "2026-02-01", "kwh": 18.1},
                "trend": "increasing",  # or "decreasing", "stable"
                "trend_percent_per_week": 5.2,
            }
        """
        pass  # IMPLEMENT: aggregate last N days
```

### 2D. Seed Demo Command

```python
# seed/management/commands/seed_demo.py

"""
Creates 5 demo subscribers with 90 days of synthetic meter data each.

Usage: python manage.py seed_demo
"""

DEMO_SUBSCRIBERS = [
    {
        "subscription_number": "01-100001-01",
        "phone_number": "+962791000001",
        "name": "أحمد الخالدي",
        "area": "عبدون",
        "household_size": 4,
        "has_ev": True,
        "home_size_sqm": 180,
        "profile": "ev_peak_charger",
    },
    {
        "subscription_number": "01-100002-01",
        "phone_number": "+962791000002",
        "name": "سارة المصري",
        "area": "الصويفية",
        "household_size": 5,
        "has_ev": False,
        "home_size_sqm": 200,
        "profile": "ac_heavy_summer",
    },
    {
        "subscription_number": "01-100003-01",
        "phone_number": "+962791000003",
        "name": "محمد العبادي",
        "area": "خلدا",
        "household_size": 3,
        "has_ev": False,
        "home_size_sqm": 120,
        "profile": "water_heater_peak",
    },
    {
        "subscription_number": "01-100004-01",
        "phone_number": "+962791000004",
        "name": "لينا حداد",
        "area": "الجبيهة",
        "household_size": 6,
        "has_ev": False,
        "home_size_sqm": 220,
        "profile": "baseline_creep",
    },
    {
        "subscription_number": "01-100005-01",
        "phone_number": "+962791000005",
        "name": "عمر الزعبي",
        "area": "دابوق",
        "household_size": 3,
        "has_ev": True,
        "home_size_sqm": 160,
        "profile": "efficient_user",
    },
]
```

### 2E. API Endpoints (Phase 2)

Add to `config/urls.py`:

```python
# Meter data endpoints
path('api/meter/<str:subscription_number>/summary/', MeterSummaryView.as_view()),
path('api/meter/<str:subscription_number>/daily/<str:date>/', MeterDailyView.as_view()),
path('api/meter/<str:subscription_number>/spikes/', MeterSpikesView.as_view()),
path('api/meter/<str:subscription_number>/forecast/', BillForecastView.as_view()),

# Tariff endpoints
path('api/tariff/current/', TouCurrentView.as_view()),
path('api/tariff/calculate/', BillCalculateView.as_view()),
```

### Phase 2 Verification

```bash
# 1. Generate demo data
python manage.py seed_demo

# 2. Check data was created
python manage.py shell
>>> from accounts.models import Subscriber
>>> Subscriber.objects.count()
5
>>> from meter.models import MeterReading
>>> MeterReading.objects.count()  # Should be ~43,200 (5 users * 96 readings/day * 90 days)

# 3. Test analyzer
>>> from meter.analyzer import MeterAnalyzer
>>> sub = Subscriber.objects.first()
>>> analyzer = MeterAnalyzer(sub)
>>> analyzer.get_consumption_summary(30)
# Should return dict with consumption data

# 4. Test spike detection
>>> analyzer.detect_spikes(7)
# Should return list of spike events

# 5. Test tariff engine
>>> from tariff.engine import get_tou_period, calculate_residential_bill
>>> get_tou_period()
# Should return current period info
>>> calculate_residential_bill(500)
# Should return bill breakdown

# 6. Test API
curl http://localhost:8000/api/tariff/current/
curl http://localhost:8000/api/meter/01-100001-01/summary/
```

---

## PHASE 3: AI Agent Core (Hours 5-8)

**Goal:** Claude-powered agent that can analyze meter data, have a conversation, and use tools. No WhatsApp yet — test via API endpoint.

### Phase 3 Deliverables
- [ ] Claude API client wrapper (supports Sonnet + Haiku, tool calling)
- [ ] Intent classifier using Haiku
- [ ] Smart Energy Detective agent with system prompt and tools
- [ ] Conversation state manager (Redis)
- [ ] RAG knowledge base ingested and searchable
- [ ] Test API endpoint: POST /api/agent/chat/ accepts message, returns agent response

### 3A. Claude API Client

```python
# core/llm_client.py

import anthropic
from django.conf import settings

client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

def chat_with_tools(
    messages: list,
    system: str,
    tools: list = None,
    model: str = "claude-sonnet-4-5-20250929",
    max_tokens: int = 1024,
) -> anthropic.types.Message:
    """
    Send a message to Claude with optional tool use.
    Handles the tool-use loop internally.
    
    Returns the final Message object after all tool calls are resolved.
    """
    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": messages,
    }
    if tools:
        kwargs["tools"] = tools

    response = client.messages.create(**kwargs)
    return response


def classify_fast(prompt: str, system: str = "") -> str:
    """
    Quick classification using Haiku. Returns raw text response.
    Used for intent detection and language classification.
    """
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text
```

### 3B. Intent Classifier

```python
# agent/intent.py

import json
from core.llm_client import classify_fast

INTENT_SYSTEM = """You are an intent classifier for a Jordanian electricity usage optimization assistant called KahrabaAI.

Classify the user message into exactly ONE intent and detect the language.

Intents:
- onboarding: User is new, wants to register, or is providing their subscription number
- bill_query: User is asking about their bill, why it's high, cost breakdown
- usage_analysis: User wants to understand their consumption patterns, see spikes, trends
- optimization_request: User wants advice on how to reduce consumption or save money
- plan_check: User is checking progress on an existing optimization plan
- tariff_question: User asking about electricity prices, TOU periods, tariff tiers
- general: Greeting, thanks, or doesn't fit other categories

Respond ONLY with valid JSON:
{"intent": "bill_query", "confidence": 0.92, "language": "ar"}
"""

INTENTS = [
    "onboarding",
    "bill_query",
    "usage_analysis",
    "optimization_request",
    "plan_check",
    "tariff_question",
    "general",
]

def classify_intent(message: str) -> dict:
    """
    Classify a user message into an intent.

    Returns:
        {"intent": str, "confidence": float, "language": "ar"|"en"}
    """
    raw = classify_fast(
        prompt=f"User message: {message}",
        system=INTENT_SYSTEM,
    )
    try:
        result = json.loads(raw.strip())
        if result.get("intent") not in INTENTS:
            result["intent"] = "general"
        return result
    except (json.JSONDecodeError, KeyError):
        return {"intent": "general", "confidence": 0.5, "language": "ar"}
```

### 3C. Agent System Prompt

```python
# agent/prompts.py

SYSTEM_PROMPT = """أنت "محقق الطاقة الذكي" — مساعد ذكاء اصطناعي يساعد مشتركي شركة الكهرباء الأردنية (JEPCO) على فهم استهلاكهم وتوفير فواتيرهم.

You are the "Smart Energy Detective" — an AI assistant that helps Jordan Electric Power Company (JEPCO) subscribers understand their electricity consumption and reduce their bills.

## Your Core Method: DETECT → INVESTIGATE → PLAN → VERIFY

1. DETECT: You have access to the subscriber's smart meter data (15-min interval readings). Use your tools to analyze it and find patterns, spikes, trends.
2. INVESTIGATE: When you find something unusual, do NOT guess the cause. Tell the user what you see in the data and ASK them what might be causing it. They know their home. You know the data.
3. PLAN: Once the user identifies the cause, create a concrete optimization plan with specific actions, expected savings in JOD, and a monitoring period.
4. VERIFY: After the monitoring period, check the meter data again and report whether the plan worked, with specific numbers.

## Your Personality
- You are like a helpful neighbor who happens to be an electricity expert
- Speak in colloquial Jordanian Arabic (اللهجة الأردنية) by default
- Switch to English seamlessly if the user writes in English
- Be warm but concise — WhatsApp messages should be SHORT (under 250 words)
- Always use concrete numbers: "وفرت 3.50 دينار" not "وفرت مبلغ"
- Use simple analogies: "سخان الماء بوكل كهربا زي 25 لمبة مشغلة مع بعض"

## Critical Rules
1. NEVER claim to know which specific appliance is consuming electricity. The meter measures TOTAL consumption only. You see patterns and spikes — not devices.
2. ALWAYS ask the user what they think is causing a pattern before suggesting a plan. Say things like: "بشوف ارتفاع كل يوم الساعة 5 المسا. شو بتعمل عادة هالوقت؟"
3. NEVER invent or hallucinate meter data. ALWAYS call your analysis tools to get real data.
4. NEVER guarantee specific savings amounts. Use "تقريباً" / "approximately".
5. For tariff rates, ALWAYS use the get_tou_period or calculate_bill tools. Never state rates from memory.
6. When creating a plan, ALWAYS include: (a) specific actions, (b) estimated savings in JOD, (c) monitoring period, (d) promise to check back.
7. If the user is new / unregistered, guide them through onboarding first.

## Conversation Awareness
- If the user asks "why is my bill high?" — first pull their consumption summary and bill forecast, THEN ask what they think changed.
- If the user says "it might be the AC" — don't just agree. Check the data: does the spike match AC patterns (afternoon/evening in summer)? Confirm or challenge with data.
- If the user has an active plan, check its progress before starting a new investigation.
- Remember the user's previous messages in this conversation (they're in the message history).

## Tools Available
Use these tools to access real data. ALWAYS use tools instead of guessing:
- get_subscriber_info: Get subscriber details and household context
- get_consumption_summary: Overall consumption stats for last N days
- get_daily_detail: Detailed breakdown of a specific day
- detect_spikes: Find unusual consumption spikes in recent data
- detect_patterns: Find recurring consumption patterns
- compare_periods: Compare two time periods (this week vs last week, etc.)
- get_bill_forecast: Predict end-of-month bill based on current trajectory
- calculate_bill: Calculate bill for a given kWh amount
- get_tou_period: Get current TOU tariff period and rates
- search_knowledge: Search tariff docs and energy saving tips
- create_plan: Create and save a new optimization plan
- get_active_plan: Get the user's current active plan
- check_plan_progress: Compare current data vs plan baseline
"""
```

### 3D. Agent Tools

```python
# agent/tools.py

TOOLS = [
    {
        "name": "get_subscriber_info",
        "description": "Get subscriber details including household size, area, whether they have EV/solar, and tariff category. Call this when you need context about the user's home.",
        "input_schema": {
            "type": "object",
            "properties": {
                "phone": {"type": "string", "description": "Phone number in E.164 format"}
            },
            "required": ["phone"]
        }
    },
    {
        "name": "get_consumption_summary",
        "description": "Get overall consumption summary for the subscriber over the last N days. Returns total kWh, average daily kWh, peak/off-peak split, highest/lowest day, cost estimate, and trend direction.",
        "input_schema": {
            "type": "object",
            "properties": {
                "phone": {"type": "string"},
                "days": {"type": "integer", "default": 30, "description": "Number of days to analyze"}
            },
            "required": ["phone"]
        }
    },
    {
        "name": "get_daily_detail",
        "description": "Get detailed consumption breakdown for a specific day. Returns hourly consumption, peak/off-peak split, max power draw, and cost by TOU period.",
        "input_schema": {
            "type": "object",
            "properties": {
                "phone": {"type": "string"},
                "date": {"type": "string", "description": "Date in YYYY-MM-DD format"}
            },
            "required": ["phone", "date"]
        }
    },
    {
        "name": "detect_spikes",
        "description": "Find unusual consumption spikes in the last N days. A spike is when power draw exceeds 2x the normal level for that hour. Returns timestamp, magnitude, duration, TOU period, and estimated extra cost.",
        "input_schema": {
            "type": "object",
            "properties": {
                "phone": {"type": "string"},
                "days": {"type": "integer", "default": 7}
            },
            "required": ["phone"]
        }
    },
    {
        "name": "detect_patterns",
        "description": "Find recurring consumption patterns over the last N days. E.g., 'Every weekday at 19:00, consumption jumps to 8 kW for 4 hours.' Returns pattern details with consistency score.",
        "input_schema": {
            "type": "object",
            "properties": {
                "phone": {"type": "string"},
                "days": {"type": "integer", "default": 14}
            },
            "required": ["phone"]
        }
    },
    {
        "name": "compare_periods",
        "description": "Compare consumption between two time periods. Use for week-over-week or month-over-month comparisons. Returns change in kWh, cost, and percentage.",
        "input_schema": {
            "type": "object",
            "properties": {
                "phone": {"type": "string"},
                "period1_start": {"type": "string", "description": "Start date YYYY-MM-DD"},
                "period1_end": {"type": "string", "description": "End date YYYY-MM-DD"},
                "period2_start": {"type": "string", "description": "Start date YYYY-MM-DD"},
                "period2_end": {"type": "string", "description": "End date YYYY-MM-DD"}
            },
            "required": ["phone", "period1_start", "period1_end", "period2_start", "period2_end"]
        }
    },
    {
        "name": "get_bill_forecast",
        "description": "Predict the end-of-month electricity bill based on consumption so far this billing cycle. Returns projected kWh, projected bill in JOD, tier reached, and comparison to last month.",
        "input_schema": {
            "type": "object",
            "properties": {
                "phone": {"type": "string"}
            },
            "required": ["phone"]
        }
    },
    {
        "name": "calculate_bill",
        "description": "Calculate the electricity bill for a given monthly kWh amount using JEPCO's tiered residential tariff. Returns total in JOD, tier breakdown, and average rate.",
        "input_schema": {
            "type": "object",
            "properties": {
                "monthly_kwh": {"type": "number", "description": "Monthly consumption in kWh"}
            },
            "required": ["monthly_kwh"]
        }
    },
    {
        "name": "get_tou_period",
        "description": "Get the current Time-of-Use tariff period. Returns period name (off-peak/partial-peak/peak), rate in fils/kWh, time remaining in current period, and next period info.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "search_knowledge",
        "description": "Search the knowledge base for information about tariffs, billing, energy saving tips, or JEPCO policies. Use when the user asks specific questions about rates or procedures.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query in Arabic or English"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "create_plan",
        "description": "Create and save a new optimization plan for the subscriber. Call this ONLY after: (1) you've detected a pattern, (2) the user confirmed what's causing it, and (3) you've agreed on specific actions. The plan includes actions, expected savings, monitoring period, and baseline data.",
        "input_schema": {
            "type": "object",
            "properties": {
                "phone": {"type": "string"},
                "detected_pattern": {"type": "string", "description": "What the agent detected in the data"},
                "user_hypothesis": {"type": "string", "description": "What the user said is causing it"},
                "plan_summary": {"type": "string", "description": "Short description of the plan"},
                "actions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "action": {"type": "string"},
                            "expected_impact_kwh": {"type": "number"},
                            "expected_savings_fils_per_day": {"type": "integer"}
                        }
                    },
                    "description": "List of specific actions for the user"
                },
                "monitoring_days": {"type": "integer", "default": 7, "description": "Days to wait before verification"}
            },
            "required": ["phone", "detected_pattern", "user_hypothesis", "plan_summary", "actions"]
        }
    },
    {
        "name": "get_active_plan",
        "description": "Get the subscriber's current active optimization plan, if any. Returns plan details, creation date, and progress status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "phone": {"type": "string"}
            },
            "required": ["phone"]
        }
    },
    {
        "name": "check_plan_progress",
        "description": "Compare current consumption data against the plan's baseline to check if the plan is working. Returns baseline vs actual, percentage change, and whether the target is being met.",
        "input_schema": {
            "type": "object",
            "properties": {
                "phone": {"type": "string"},
                "plan_id": {"type": "integer"}
            },
            "required": ["phone", "plan_id"]
        }
    },
]
```

### 3E. Tool Execution

```python
# agent/tools.py (continued)

def execute_tool(tool_name: str, tool_input: dict) -> str:
    """
    Execute an agent tool and return the result as a JSON string.

    This function maps tool names to actual service calls.
    All results are serialized to JSON for the agent to consume.
    """
    import json
    from accounts.models import Subscriber
    from meter.analyzer import MeterAnalyzer
    from tariff.engine import get_tou_period, calculate_residential_bill
    from plans.services import create_optimization_plan, get_active_plan, check_progress
    from rag.retriever import search

    # Helper to get subscriber from phone
    def get_sub(phone):
        return Subscriber.objects.get(phone_number=phone)

    try:
        if tool_name == "get_subscriber_info":
            sub = get_sub(tool_input["phone"])
            return json.dumps({
                "name": sub.name,
                "subscription_number": sub.subscription_number,
                "area": sub.area,
                "tariff_category": sub.tariff_category,
                "household_size": sub.household_size,
                "has_ev": sub.has_ev,
                "has_solar": sub.has_solar,
                "home_size_sqm": sub.home_size_sqm,
                "language": sub.language,
            }, ensure_ascii=False)

        elif tool_name == "get_consumption_summary":
            sub = get_sub(tool_input["phone"])
            analyzer = MeterAnalyzer(sub)
            result = analyzer.get_consumption_summary(days=tool_input.get("days", 30))
            return json.dumps(result, ensure_ascii=False, default=str)

        elif tool_name == "get_daily_detail":
            sub = get_sub(tool_input["phone"])
            analyzer = MeterAnalyzer(sub)
            from datetime import date as d
            target = d.fromisoformat(tool_input["date"])
            result = analyzer.get_daily_summary(target)
            return json.dumps(result, ensure_ascii=False, default=str)

        elif tool_name == "detect_spikes":
            sub = get_sub(tool_input["phone"])
            analyzer = MeterAnalyzer(sub)
            result = analyzer.detect_spikes(days=tool_input.get("days", 7))
            return json.dumps(result, ensure_ascii=False, default=str)

        elif tool_name == "detect_patterns":
            sub = get_sub(tool_input["phone"])
            analyzer = MeterAnalyzer(sub)
            result = analyzer.detect_recurring_pattern(days=tool_input.get("days", 14))
            return json.dumps(result, ensure_ascii=False, default=str)

        elif tool_name == "compare_periods":
            sub = get_sub(tool_input["phone"])
            analyzer = MeterAnalyzer(sub)
            from datetime import date as d
            result = analyzer.compare_periods(
                d.fromisoformat(tool_input["period1_start"]),
                d.fromisoformat(tool_input["period1_end"]),
                d.fromisoformat(tool_input["period2_start"]),
                d.fromisoformat(tool_input["period2_end"]),
            )
            return json.dumps(result, ensure_ascii=False, default=str)

        elif tool_name == "get_bill_forecast":
            sub = get_sub(tool_input["phone"])
            analyzer = MeterAnalyzer(sub)
            result = analyzer.get_bill_forecast()
            return json.dumps(result, ensure_ascii=False, default=str)

        elif tool_name == "calculate_bill":
            result = calculate_residential_bill(tool_input["monthly_kwh"])
            return json.dumps(result, ensure_ascii=False)

        elif tool_name == "get_tou_period":
            result = get_tou_period()
            return json.dumps(result, ensure_ascii=False)

        elif tool_name == "search_knowledge":
            results = search(tool_input["query"], n_results=3)
            return json.dumps(results, ensure_ascii=False)

        elif tool_name == "create_plan":
            sub = get_sub(tool_input["phone"])
            plan = create_optimization_plan(sub, tool_input)
            return json.dumps({
                "plan_id": plan.id,
                "status": "created",
                "verify_after": str(plan.verify_after_date),
                "message": "Plan saved. Will check results after monitoring period."
            }, ensure_ascii=False)

        elif tool_name == "get_active_plan":
            sub = get_sub(tool_input["phone"])
            plan = get_active_plan(sub)
            if plan:
                return json.dumps({
                    "plan_id": plan.id,
                    "summary": plan.plan_summary,
                    "status": plan.status,
                    "created_at": str(plan.created_at.date()),
                    "verify_after": str(plan.verify_after_date),
                    "user_hypothesis": plan.user_hypothesis,
                    "actions": plan.plan_details.get("actions", []),
                }, ensure_ascii=False)
            return json.dumps({"plan": None, "message": "No active plan"})

        elif tool_name == "check_plan_progress":
            sub = get_sub(tool_input["phone"])
            result = check_progress(sub, tool_input["plan_id"])
            return json.dumps(result, ensure_ascii=False, default=str)

        else:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})

    except Subscriber.DoesNotExist:
        return json.dumps({"error": "Subscriber not found. They may need to register first."})
    except Exception as e:
        return json.dumps({"error": str(e)})
```

### 3F. Main Agent

```python
# agent/coach.py

from core.llm_client import chat_with_tools
from agent.prompts import SYSTEM_PROMPT
from agent.tools import TOOLS, execute_tool
from agent.intent import classify_intent
from agent.conversation import ConversationManager

class EnergyDetective:
    """
    Main agent class. Handles a single user message end-to-end.
    """

    def __init__(self):
        self.conv_manager = ConversationManager()

    def handle_message(self, phone: str, message: str) -> str:
        """
        Process an incoming message and return the agent's response.

        Steps:
        1. Load conversation history from Redis
        2. Classify intent (Haiku — fast)
        3. Add user context to message
        4. Send to Claude Sonnet with tools
        5. Execute any tool calls in a loop
        6. Return final text response
        7. Save conversation history to Redis
        """
        # 1. Load conversation state
        state = self.conv_manager.get_state(phone)
        history = state.get("messages", [])

        # 2. Classify intent
        intent_result = classify_intent(message)
        language = intent_result.get("language", "ar")

        # 3. Build user message with context
        user_content = message

        # 4. Append to history
        history.append({"role": "user", "content": user_content})

        # 5. Call Claude with tools
        response = chat_with_tools(
            messages=history,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            model="claude-sonnet-4-5-20250929",
            max_tokens=1024,
        )

        # 6. Tool use loop
        while response.stop_reason == "tool_use":
            # Build assistant message with tool calls
            assistant_content = []
            tool_results = []

            for block in response.content:
                if block.type == "text":
                    assistant_content.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    assistant_content.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })
                    # Execute the tool
                    result = execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            history.append({"role": "assistant", "content": assistant_content})
            history.append({"role": "user", "content": tool_results})

            # Call Claude again with tool results
            response = chat_with_tools(
                messages=history,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                model="claude-sonnet-4-5-20250929",
                max_tokens=1024,
            )

        # 7. Extract final text
        final_text = ""
        assistant_content = []
        for block in response.content:
            if block.type == "text":
                final_text += block.text
                assistant_content.append({"type": "text", "text": block.text})

        history.append({"role": "assistant", "content": assistant_content})

        # 8. Save conversation state (keep last 20 messages to manage context window)
        state["messages"] = history[-20:]
        state["language"] = language
        state["last_intent"] = intent_result.get("intent")
        self.conv_manager.save_state(phone, state)

        return final_text
```

### 3G. Conversation State Manager

```python
# agent/conversation.py

import json
import redis
from django.conf import settings

class ConversationManager:
    """
    Manages conversation state in Redis.
    Each phone number gets a conversation state with 30-minute TTL.
    """

    def __init__(self):
        self.redis = redis.from_url(settings.REDIS_URL)
        self.ttl = 1800  # 30 minutes

    def _key(self, phone: str) -> str:
        return f"conv:{phone}"

    def get_state(self, phone: str) -> dict:
        raw = self.redis.get(self._key(phone))
        if raw:
            return json.loads(raw)
        return {"messages": [], "language": "ar", "last_intent": None}

    def save_state(self, phone: str, state: dict):
        self.redis.setex(
            self._key(phone),
            self.ttl,
            json.dumps(state, ensure_ascii=False, default=str),
        )

    def clear_state(self, phone: str):
        self.redis.delete(self._key(phone))
```

### 3H. Test API Endpoint (temporary, for testing without WhatsApp)

```python
# agent/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from agent.coach import EnergyDetective

class AgentChatView(APIView):
    """
    Temporary test endpoint. Send messages to the agent without WhatsApp.
    
    POST /api/agent/chat/
    Body: {"phone": "+962791000001", "message": "ليش فاتورتي غالية؟"}
    """
    def post(self, request):
        phone = request.data.get("phone")
        message = request.data.get("message")
        
        if not phone or not message:
            return Response({"error": "phone and message required"}, status=400)
        
        agent = EnergyDetective()
        reply = agent.handle_message(phone, message)
        
        return Response({
            "reply": reply,
            "phone": phone,
        })
```

Add to urls.py:
```python
path('api/agent/chat/', AgentChatView.as_view()),
```

### Phase 3 Verification

```bash
# 1. Make sure demo data exists
python manage.py seed_demo

# 2. Test intent classifier
python manage.py shell
>>> from agent.intent import classify_intent
>>> classify_intent("ليش فاتورتي غالية؟")
# Should return: {"intent": "bill_query", "confidence": ~0.9, "language": "ar"}
>>> classify_intent("what are the peak hours?")
# Should return: {"intent": "tariff_question", "confidence": ~0.9, "language": "en"}

# 3. Test agent via API
curl -X POST http://localhost:8000/api/agent/chat/ \
  -H "Content-Type: application/json" \
  -d '{"phone": "+962791000001", "message": "مرحبا"}'
# Should return a greeting response

curl -X POST http://localhost:8000/api/agent/chat/ \
  -H "Content-Type: application/json" \
  -d '{"phone": "+962791000001", "message": "ليش فاتورتي غالية هالشهر؟"}'
# Should return: agent analyzes consumption, asks user what changed

curl -X POST http://localhost:8000/api/agent/chat/ \
  -H "Content-Type: application/json" \
  -d '{"phone": "+962791000001", "message": "بشحن سيارتي كل يوم لما برجع عالبيت الساعة 7"}'
# Should return: agent confirms this matches the peak spike, suggests a plan
```

---

## PHASE 4: WhatsApp Integration (Hours 8-10)

**Goal:** Connect the agent to WhatsApp. Messages in WhatsApp → agent → reply in WhatsApp.

### Phase 4 Deliverables
- [ ] WhatsApp webhook receives and verifies messages
- [ ] Incoming messages are processed via Celery (async)
- [ ] Agent replies are sent back via WhatsApp API
- [ ] Interactive button messages work (for quick replies)
- [ ] Onboarding flow: new user → ask subscription number → register
- [ ] Error handling: graceful fallback if Claude API fails

### 4A. Webhook Handler

```python
# whatsapp/webhook.py

import hashlib
import hmac
import json
from django.conf import settings
from django.http import HttpResponse
from rest_framework.decorators import api_view
from whatsapp.tasks import process_incoming_message

@api_view(['GET', 'POST'])
def whatsapp_webhook(request):
    """
    WhatsApp Cloud API webhook handler.
    
    GET: Verification challenge from Meta during webhook setup.
    POST: Incoming messages and status updates.
    """
    if request.method == 'GET':
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')

        if mode == 'subscribe' and token == settings.WHATSAPP_VERIFY_TOKEN:
            return HttpResponse(challenge, status=200, content_type='text/plain')
        return HttpResponse('Forbidden', status=403)

    if request.method == 'POST':
        # Verify signature
        signature = request.headers.get('X-Hub-Signature-256', '')
        if not verify_webhook_signature(request.body, signature):
            return HttpResponse('Invalid signature', status=401)

        payload = json.loads(request.body)

        # Extract messages
        for entry in payload.get('entry', []):
            for change in entry.get('changes', []):
                value = change.get('value', {})

                # Handle incoming messages
                for message in value.get('messages', []):
                    phone = message['from']  # sender phone number
                    msg_type = message.get('type')

                    text = ""
                    if msg_type == 'text':
                        text = message['text']['body']
                    elif msg_type == 'interactive':
                        # Button reply or list reply
                        interactive = message.get('interactive', {})
                        if interactive.get('type') == 'button_reply':
                            text = interactive['button_reply']['title']
                        elif interactive.get('type') == 'list_reply':
                            text = interactive['list_reply']['title']

                    if text:
                        # Process asynchronously
                        process_incoming_message.delay(phone, text)

        return HttpResponse('OK', status=200)


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """Verify the X-Hub-Signature-256 header."""
    if not settings.WHATSAPP_APP_SECRET:
        return True  # Skip in dev if no secret configured
    
    expected = 'sha256=' + hmac.new(
        settings.WHATSAPP_APP_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected, signature)
```

### 4B. Message Sender

```python
# whatsapp/sender.py

import httpx
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

API_URL = "https://graph.facebook.com/v21.0"

def _get_headers():
    return {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

def _send(payload: dict):
    """Send a message via WhatsApp Cloud API."""
    url = f"{API_URL}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    try:
        response = httpx.post(url, json=payload, headers=_get_headers(), timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"WhatsApp send failed: {e}")
        return None


def send_text(phone: str, text: str):
    """Send a plain text message."""
    _send({
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": text},
    })


def send_buttons(phone: str, body: str, buttons: list[dict]):
    """
    Send interactive button message.
    
    buttons: [{"id": "btn_1", "title": "نعم"}]  — max 3 buttons, title max 20 chars
    """
    _send({
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": btn} for btn in buttons
                ]
            }
        },
    })


def send_list(phone: str, body: str, button_text: str, sections: list[dict]):
    """
    Send interactive list message.

    sections: [{
        "title": "Section",
        "rows": [{"id": "row_1", "title": "Option", "description": "Details"}]
    }]
    """
    _send({
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": body},
            "action": {
                "button": button_text,
                "sections": sections,
            }
        },
    })
```

### 4C. Async Message Processing

```python
# whatsapp/tasks.py

from celery import shared_task
from agent.coach import EnergyDetective
from whatsapp.sender import send_text, send_buttons
from accounts.models import Subscriber
import logging

logger = logging.getLogger(__name__)

FALLBACK_MESSAGE_AR = "عذراً، في مشكلة تقنية حالياً. حاول مرة ثانية بعد شوي. 🔧"
FALLBACK_MESSAGE_EN = "Sorry, there's a technical issue right now. Please try again shortly. 🔧"

ONBOARDING_MESSAGE_AR = """مرحباً بك في كهرباءAI — محقق الطاقة الذكي! ⚡🔍

أنا مساعدك الشخصي لفهم استهلاكك للكهربا وتوفير فاتورتك.

عشان أبدأ، أعطيني رقم اشتراكك بشركة الكهرباء (JEPCO).
بتلاقيه على فاتورتك، شكله هيك: 01-XXXXXX-XX"""

@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def process_incoming_message(self, phone: str, text: str):
    """
    Process a WhatsApp message asynchronously.
    
    Handles:
    - New users → onboarding flow
    - Registered users → agent processing
    - Errors → fallback message
    """
    try:
        # Check if subscriber exists
        try:
            subscriber = Subscriber.objects.get(phone_number=phone)
        except Subscriber.DoesNotExist:
            # Check if text looks like a subscription number
            if _looks_like_subscription_number(text.strip()):
                _handle_registration(phone, text.strip())
                return
            
            # New user — start onboarding
            send_text(phone, ONBOARDING_MESSAGE_AR)
            return

        # Existing subscriber — process with agent
        agent = EnergyDetective()
        reply = agent.handle_message(phone, text)
        
        # Send reply (split if too long for WhatsApp)
        if len(reply) > 4000:
            # Split at last paragraph before 4000 chars
            split_point = reply[:4000].rfind('\n\n')
            if split_point == -1:
                split_point = 4000
            send_text(phone, reply[:split_point])
            send_text(phone, reply[split_point:])
        else:
            send_text(phone, reply)

    except Exception as e:
        logger.error(f"Error processing message from {phone}: {e}", exc_info=True)
        send_text(phone, FALLBACK_MESSAGE_AR)


def _looks_like_subscription_number(text: str) -> bool:
    """Check if text matches JEPCO subscription number pattern: XX-XXXXXX-XX"""
    import re
    pattern = r'^\d{2}-\d{6}-\d{2}$'
    return bool(re.match(pattern, text.replace(' ', '')))


def _handle_registration(phone: str, subscription_number: str):
    """Register a new subscriber."""
    # In production: verify against JEPCO API
    # In demo: create subscriber directly
    subscriber, created = Subscriber.objects.get_or_create(
        subscription_number=subscription_number,
        defaults={
            "phone_number": phone,
            "language": "ar",
            "is_verified": True,
        }
    )
    
    if created:
        # Generate synthetic data for new subscriber
        from meter.generator import generate_meter_data
        from meter.models import MeterReading
        readings = generate_meter_data(subscriber, "ac_heavy_summer", days=90)
        MeterReading.objects.bulk_create(readings, batch_size=1000)
        
        send_text(phone, f"تم تسجيلك بنجاح! ✅\nرقم الاشتراك: {subscription_number}\n\nهلأ اسألني أي سؤال عن استهلاكك أو فاتورتك. مثلاً:\n• ليش فاتورتي غالية؟\n• شو استهلاكي هالأسبوع؟\n• كيف أوفر؟")
    elif subscriber.phone_number != phone:
        send_text(phone, "رقم الاشتراك هذا مسجل على رقم ثاني. تواصل مع JEPCO للمساعدة.")
    else:
        send_text(phone, f"مرحباً مجدداً! حسابك مسجل. كيف أقدر أساعدك؟")
```

### 4D. URL Configuration

Add to urls.py:
```python
path('api/whatsapp/webhook/', whatsapp_webhook, name='whatsapp-webhook'),
```

### Phase 4 Verification

```bash
# 1. Start Celery worker
celery -A config worker -l info

# 2. Start ngrok
ngrok http 8000

# 3. Configure Meta WhatsApp webhook with ngrok URL
# Set webhook URL: https://xxxx.ngrok.io/api/whatsapp/webhook/
# Set verify token: kahrabaai-verify-token

# 4. Send a message to the WhatsApp number
# New user → should get onboarding message
# Send subscription number → should register
# Send "ليش فاتورتي غالية؟" → should get agent response
```

---

## PHASE 5: Investigation & Plan Engine (Hours 10-13)

**Goal:** The full DETECT → INVESTIGATE → PLAN → VERIFY loop works end-to-end.

### Phase 5 Deliverables
- [ ] Plan creation service saves plans with baseline data
- [ ] Plan progress checking compares current vs baseline
- [ ] Plan verification runs automatically after monitoring period
- [ ] RAG knowledge base ingested with tariff docs and FAQs
- [ ] Celery scheduled tasks: weekly report, spike alert, plan check-in
- [ ] Full demo conversation flow works end-to-end

### 5A. Plan Services

```python
# plans/services.py

from datetime import date, timedelta
from plans.models import OptimizationPlan, PlanCheckpoint
from meter.analyzer import MeterAnalyzer
from tariff.engine import calculate_residential_bill

def create_optimization_plan(subscriber, plan_data: dict) -> OptimizationPlan:
    """
    Create a new optimization plan with baseline snapshot.
    
    1. Snapshot current consumption as baseline
    2. Set verification date (today + monitoring_days)
    3. Save plan with all details
    """
    analyzer = MeterAnalyzer(subscriber)
    summary = analyzer.get_consumption_summary(days=30)
    
    baseline_daily = summary["avg_daily_kwh"]
    baseline_peak = summary.get("peak_kwh_avg_daily", baseline_daily * 0.4)
    baseline_monthly = calculate_residential_bill(baseline_daily * 30)["total_fils"]
    
    monitoring_days = plan_data.get("monitoring_days", 7)
    
    plan = OptimizationPlan.objects.create(
        subscriber=subscriber,
        detected_pattern=plan_data["detected_pattern"],
        user_hypothesis=plan_data["user_hypothesis"],
        plan_summary=plan_data["plan_summary"],
        plan_details={
            "actions": plan_data.get("actions", []),
            "monitoring_period_days": monitoring_days,
        },
        baseline_daily_kwh=baseline_daily,
        baseline_peak_kwh=baseline_peak,
        baseline_monthly_cost_fils=baseline_monthly,
        status="active",
        verify_after_date=date.today() + timedelta(days=monitoring_days),
    )
    
    return plan


def get_active_plan(subscriber) -> OptimizationPlan:
    """Get the most recent active or monitoring plan."""
    return OptimizationPlan.objects.filter(
        subscriber=subscriber,
        status__in=["active", "monitoring"],
    ).order_by("-created_at").first()


def check_progress(subscriber, plan_id: int) -> dict:
    """
    Compare current consumption against plan baseline.
    
    Returns comparison data the agent can use to inform the user.
    """
    plan = OptimizationPlan.objects.get(id=plan_id, subscriber=subscriber)
    analyzer = MeterAnalyzer(subscriber)
    
    # Get data since plan was created
    days_since = (date.today() - plan.created_at.date()).days
    if days_since < 1:
        days_since = 1
    
    current = analyzer.get_consumption_summary(days=min(days_since, 30))
    
    current_daily = current["avg_daily_kwh"]
    change = current_daily - plan.baseline_daily_kwh
    change_pct = (change / plan.baseline_daily_kwh) * 100 if plan.baseline_daily_kwh > 0 else 0
    
    # Calculate cost impact
    current_monthly_estimate = calculate_residential_bill(current_daily * 30)["total_fils"]
    savings_fils = plan.baseline_monthly_cost_fils - current_monthly_estimate
    
    result = {
        "plan_id": plan.id,
        "plan_summary": plan.plan_summary,
        "days_since_start": days_since,
        "baseline_daily_kwh": round(plan.baseline_daily_kwh, 1),
        "current_daily_kwh": round(current_daily, 1),
        "change_kwh": round(change, 1),
        "change_percent": round(change_pct, 1),
        "estimated_monthly_savings_fils": savings_fils,
        "estimated_monthly_savings_jod": round(savings_fils / 1000, 2),
        "is_improving": change < 0,
        "ready_for_verification": date.today() >= plan.verify_after_date,
    }
    
    # Save checkpoint
    PlanCheckpoint.objects.create(
        plan=plan,
        check_date=date.today(),
        avg_daily_kwh=current_daily,
        avg_peak_kwh=current.get("peak_kwh_avg_daily", current_daily * 0.4),
        avg_offpeak_kwh=current.get("offpeak_kwh_avg_daily", current_daily * 0.35),
        estimated_cost_fils_per_day=int(current_monthly_estimate / 30),
        change_vs_baseline_percent=round(change_pct, 1),
    )
    
    return result
```

### 5B. RAG Knowledge Base

Create the following documents in `rag/documents/`:

**tou_tariffs.md:**
```markdown
# تعرفة الكهرباء حسب الوقت - الأردن
# Jordan Time-of-Use (TOU) Electricity Tariffs

## TOU Periods
- Off-Peak (خارج الذروة): 05:00 - 14:00 — cheapest rates, aligned with solar generation
- Partial Peak (ذروة جزئية): 14:00 - 17:00 AND 23:00 - 05:00
- Peak (وقت الذروة): 17:00 - 23:00 — most expensive, highest grid demand

## EV Charging Rates (Home Meter)
- Off-Peak: 108 fils/kWh
- Partial Peak: 118 fils/kWh  
- Peak: 160 fils/kWh

## EV Charging Rates (Public Stations)
- Off-Peak: 103 fils/kWh
- Partial Peak: 113 fils/kWh
- Peak: 133 fils/kWh

Source: Energy and Minerals Regulatory Commission (EMRC), effective July 2025.
Note: 1 JOD = 1000 fils.
TOU tariffs currently apply to EV charging, industrial, and water pumping sectors.
Residential tariff is still tiered (block-based), not TOU — but expected to expand.
```

**jepco_tariff_tiers.md:**
```markdown
# JEPCO Residential Electricity Tariff (Tiered)

Monthly consumption tiers and rates:
- Tier 1: First 160 kWh → 33 fils/kWh
- Tier 2: 161-320 kWh → 72 fils/kWh
- Tier 3: 321-480 kWh → 86 fils/kWh
- Tier 4: 481-640 kWh → 114 fils/kWh
- Tier 5: 641-800 kWh → 158 fils/kWh
- Tier 6: 801-1000 kWh → 200 fils/kWh
- Tier 7: Above 1000 kWh → 265 fils/kWh

Fixed monthly charge:
- Single phase: 500 fils (0.5 JOD)
- Three phase: 1500 fils (1.5 JOD)

Important: The tiered system means every extra kWh gets more expensive.
Reducing consumption by even 50 kWh/month can drop you to a lower tier,
saving significantly more than just the 50 kWh worth of electricity.

Example:
- 500 kWh/month → ~38.38 JOD
- 450 kWh/month → ~33.14 JOD (saving 5.24 JOD = 13.6% reduction for 10% less usage)
```

**energy_saving_tips.md:**
```markdown
# نصائح توفير الطاقة - Energy Saving Tips for Jordanian Homes

## Air Conditioning (المكيف)
- Every 1°C higher on thermostat saves ~8% on AC electricity
- Set to 24°C instead of 20°C: saves approximately 30% on AC costs
- Pre-cool home during off-peak hours (before 5 PM) if on TOU tariff
- Clean filters monthly: dirty filters increase consumption by 15-25%
- Close curtains on sun-facing windows during afternoon
- Use fans alongside AC to feel cooler at higher thermostat settings

## Water Heater (سخان الماء)
- Electric water heaters draw 2-4 kW — one of the highest single loads in a home
- Use a timer to heat water during off-peak hours (5 AM - 2 PM)
- Reduce temperature setting from 60°C to 50°C: saves ~10% with minimal comfort impact
- Consider solar water heater: Jordan gets 300+ sunny days per year
- Insulate hot water pipes to reduce heat loss

## EV Charging (شحن السيارة الكهربائية)
- Level 2 home charging draws 3-7 kW for 4-8 hours
- Charging at peak (5-11 PM) costs 160 fils/kWh
- Charging at off-peak (5 AM - 2 PM) costs 108 fils/kWh
- Difference: 32.5% savings by shifting charge time
- Use the car's built-in charge timer to schedule overnight or morning charging

## Lighting
- Replace incandescent bulbs with LED: uses 75% less electricity
- One LED bulb = 10W vs incandescent = 60W
- A home with 20 bulbs: LED saves ~1 kWh/day = 30 kWh/month

## General
- Unplug chargers, TVs on standby, unused appliances: standby power = 5-10% of total bill
- Use washing machine and dishwasher during off-peak hours
- Full loads only: half-load uses nearly the same energy as full load
```

**billing_faq_ar.md:** Arabic FAQ about billing, reading the bill, disputing charges  
**billing_faq_en.md:** English version

### 5C. RAG Ingestion

```python
# rag/ingest.py

import os
import chromadb
from sentence_transformers import SentenceTransformer
from django.conf import settings

def chunk_text(text: str, chunk_size: int = 512, overlap: int = 128) -> list[str]:
    """Split text into overlapping chunks by approximate token count (words * 1.3)."""
    words = text.split()
    chunk_words = chunk_size  # approximate
    overlap_words = overlap
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_words
        chunk = ' '.join(words[start:end])
        chunks.append(chunk)
        start += chunk_words - overlap_words
    return chunks


def ingest_all():
    """Ingest all documents in rag/documents/ into ChromaDB."""
    docs_dir = os.path.join(os.path.dirname(__file__), 'documents')
    
    client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
    collection = client.get_or_create_collection(
        name="kahrabaai_knowledge",
        metadata={"hnsw:space": "cosine"}
    )
    
    model = SentenceTransformer("intfloat/multilingual-e5-large")
    
    for filename in os.listdir(docs_dir):
        if not filename.endswith('.md'):
            continue
        filepath = os.path.join(docs_dir, filename)
        text = open(filepath, 'r', encoding='utf-8').read()
        chunks = chunk_text(text)
        
        for i, chunk in enumerate(chunks):
            doc_id = f"{filename}_{i}"
            embedding = model.encode(f"passage: {chunk}").tolist()
            
            collection.upsert(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[{
                    "source": filename,
                    "language": "ar" if "_ar" in filename else "en" if "_en" in filename else "both",
                    "chunk_index": i,
                }],
            )
    
    print(f"Ingested {collection.count()} chunks into ChromaDB.")
```

```python
# rag/retriever.py

import chromadb
from sentence_transformers import SentenceTransformer
from django.conf import settings

_model = None
_collection = None

def _get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
        _collection = client.get_or_create_collection("kahrabaai_knowledge")
    return _collection

def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("intfloat/multilingual-e5-large")
    return _model

def search(query: str, n_results: int = 3) -> list[dict]:
    """Search the knowledge base. Returns list of {text, source, score}."""
    model = _get_model()
    collection = _get_collection()
    
    embedding = model.encode(f"query: {query}").tolist()
    
    results = collection.query(
        query_embeddings=[embedding],
        n_results=n_results,
    )
    
    output = []
    for i in range(len(results['documents'][0])):
        output.append({
            "text": results['documents'][0][i],
            "source": results['metadatas'][0][i].get('source', ''),
            "score": 1 - results['distances'][0][i],  # Convert distance to similarity
        })
    
    return output
```

### 5D. Scheduled Notifications

```python
# notifications/tasks.py

from celery import shared_task
from datetime import date, timedelta
from accounts.models import Subscriber
from meter.analyzer import MeterAnalyzer
from plans.models import OptimizationPlan
from plans.services import check_progress
from whatsapp.sender import send_text

@shared_task
def send_weekly_reports():
    """
    Sunday 10 AM: Send weekly consumption summary to all subscribers.
    """
    for sub in Subscriber.objects.filter(wants_weekly_report=True, is_verified=True):
        try:
            analyzer = MeterAnalyzer(sub)
            
            # This week vs last week
            today = date.today()
            this_week_start = today - timedelta(days=7)
            last_week_start = today - timedelta(days=14)
            
            comparison = analyzer.compare_periods(
                last_week_start, this_week_start - timedelta(days=1),
                this_week_start, today,
            )
            
            summary = analyzer.get_consumption_summary(days=7)
            
            lang = sub.language
            if lang == 'ar':
                msg = f"📊 تقريرك الأسبوعي:\n\n"
                msg += f"⚡ الاستهلاك: {summary['total_kwh']:.0f} كيلوواط\n"
                msg += f"💰 التكلفة التقريبية: {summary['avg_daily_cost_fils'] * 7 / 1000:.1f} دينار\n"
                if comparison['improved']:
                    msg += f"✅ تحسن {abs(comparison['change_percent']):.0f}% عن الأسبوع الماضي!\n"
                else:
                    msg += f"📈 زيادة {comparison['change_percent']:.0f}% عن الأسبوع الماضي\n"
                msg += f"\nاسألني 'كيف أوفر؟' وبساعدك 💡"
            else:
                msg = f"📊 Your weekly report:\n\n"
                msg += f"⚡ Usage: {summary['total_kwh']:.0f} kWh\n"
                msg += f"💰 Est. cost: JOD {summary['avg_daily_cost_fils'] * 7 / 1000:.1f}\n"
                if comparison['improved']:
                    msg += f"✅ Down {abs(comparison['change_percent']):.0f}% from last week!\n"
                else:
                    msg += f"📈 Up {comparison['change_percent']:.0f}% from last week\n"
                msg += f"\nAsk me 'how can I save?' for tips 💡"
            
            send_text(sub.phone_number, msg)
        except Exception as e:
            import logging
            logging.error(f"Weekly report failed for {sub.subscription_number}: {e}")


@shared_task
def check_spike_alerts():
    """
    Run every 4 hours: Check for unusual spikes and alert subscribers.
    """
    for sub in Subscriber.objects.filter(wants_spike_alerts=True, is_verified=True):
        try:
            analyzer = MeterAnalyzer(sub)
            spikes = analyzer.detect_spikes(days=1, threshold_factor=2.5)
            
            if spikes:
                biggest = max(spikes, key=lambda s: s['spike_factor'])
                
                if sub.language == 'ar':
                    msg = f"⚠️ تنبيه استهلاك!\n\n"
                    msg += f"لاحظت ارتفاع غير عادي: {biggest['power_kw']:.1f} كيلوواط "
                    msg += f"الساعة {biggest['timestamp'].split('T')[1][:5]}\n"
                    msg += f"هذا {biggest['spike_factor']:.1f}x أعلى من المعتاد.\n\n"
                    msg += f"شو كان مشغل عندك هالوقت؟"
                else:
                    msg = f"⚠️ Usage alert!\n\n"
                    msg += f"Unusual spike detected: {biggest['power_kw']:.1f} kW "
                    msg += f"at {biggest['timestamp'].split('T')[1][:5]}\n"
                    msg += f"That's {biggest['spike_factor']:.1f}x your normal level.\n\n"
                    msg += f"What was running at that time?"
                
                send_text(sub.phone_number, msg)
        except Exception:
            pass


@shared_task
def check_plan_verifications():
    """
    Run daily at 9 AM: Check if any plans are ready for verification.
    """
    plans_due = OptimizationPlan.objects.filter(
        status__in=["active", "monitoring"],
        verify_after_date__lte=date.today(),
    )
    
    for plan in plans_due:
        try:
            sub = plan.subscriber
            result = check_progress(sub, plan.id)
            
            if sub.language == 'ar':
                msg = f"📋 نتائج خطتك!\n\n"
                msg += f"الخطة: {plan.plan_summary}\n\n"
                if result['is_improving']:
                    msg += f"✅ استهلاكك نزل {abs(result['change_percent']):.0f}%!\n"
                    msg += f"💰 توفير شهري تقريبي: {result['estimated_monthly_savings_jod']:.1f} دينار\n"
                    msg += f"\nممتاز! كمّل على هالنظام 💪"
                else:
                    msg += f"📊 استهلاكك زاد {result['change_percent']:.0f}%\n"
                    msg += f"يمكن نحتاج نعدل الخطة. شو بتقترح؟"
            else:
                msg = f"📋 Plan results!\n\n"
                msg += f"Plan: {plan.plan_summary}\n\n"
                if result['is_improving']:
                    msg += f"✅ Your usage dropped {abs(result['change_percent']):.0f}%!\n"
                    msg += f"💰 Est. monthly savings: JOD {result['estimated_monthly_savings_jod']:.1f}\n"
                    msg += f"\nGreat work! Keep it up 💪"
                else:
                    msg += f"📊 Usage increased {result['change_percent']:.0f}%\n"
                    msg += f"We may need to adjust the plan. What do you think?"
            
            send_text(sub.phone_number, msg)
            
            # Update plan status
            plan.status = "verified"
            plan.verification_result = result
            plan.save()
            
        except Exception as e:
            import logging
            logging.error(f"Plan verification failed for plan {plan.id}: {e}")
```

### 5E. Celery Beat Schedule

```python
# In config/celery.py or config/settings.py

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'weekly-reports': {
        'task': 'notifications.tasks.send_weekly_reports',
        'schedule': crontab(hour=10, minute=0, day_of_week=0),  # Sunday 10 AM
    },
    'spike-alerts': {
        'task': 'notifications.tasks.check_spike_alerts',
        'schedule': crontab(hour='*/4', minute=30),  # Every 4 hours at :30
    },
    'plan-verifications': {
        'task': 'notifications.tasks.check_plan_verifications',
        'schedule': crontab(hour=9, minute=0),  # Daily at 9 AM
    },
}
```

### Phase 5 Verification

Test the complete flow via API (or WhatsApp if already connected):

```bash
# Full conversation flow test:

# 1. User asks why bill is high
curl -X POST http://localhost:8000/api/agent/chat/ \
  -d '{"phone": "+962791000001", "message": "ليش فاتورتي غالية هالشهر؟"}'
# Agent should: pull consumption summary, show the spike pattern, ASK user what's causing it

# 2. User identifies cause
curl -X POST http://localhost:8000/api/agent/chat/ \
  -d '{"phone": "+962791000001", "message": "أنا بشحن سيارتي كل يوم الساعة 7 بالليل"}'
# Agent should: confirm this matches the 7 PM spike, explain peak pricing, suggest a plan

# 3. User agrees to plan
curl -X POST http://localhost:8000/api/agent/chat/ \
  -d '{"phone": "+962791000001", "message": "تمام خلينا نجرب"}'
# Agent should: create plan, set monitoring period, confirm will check back

# 4. User checks progress later
curl -X POST http://localhost:8000/api/agent/chat/ \
  -d '{"phone": "+962791000001", "message": "كيف ماشية الخطة؟"}'
# Agent should: check_plan_progress, report current vs baseline
```

---

## PHASE 6: Polish & Demo (Hours 13-15)

**Goal:** Everything works smoothly, edge cases handled, demo-ready.

### Phase 6 Deliverables
- [ ] Error handling: no unhandled exceptions crash the agent
- [ ] Rate limiting: max 30 messages per phone per hour
- [ ] Long message handling: messages split at 4000 chars
- [ ] All 5 demo subscribers have distinctive data patterns
- [ ] Demo script tested end-to-end on WhatsApp
- [ ] Edge cases: empty messages, unknown subscription numbers, rapid messages

### 6A. Rate Limiting

```python
# In whatsapp/tasks.py, add to process_incoming_message:

def _check_rate_limit(phone: str) -> bool:
    """Allow max 30 messages per phone per hour."""
    import redis as r
    redis = r.from_url(settings.REDIS_URL)
    key = f"rate:{phone}"
    count = redis.incr(key)
    if count == 1:
        redis.expire(key, 3600)  # 1 hour window
    return count <= 30
```

### 6B. Demo Script

Walk through this exact sequence during the presentation:

**Demo 1: The EV Peak Charger (أحمد)**
1. Send: `مرحبا` → Agent greets
2. Send: `ليش فاتورتي غالية؟` → Agent analyzes, finds 7 PM spike, asks what's happening
3. Send: `بشحن سيارتي لما بوصل عالبيت` → Agent confirms spike matches EV charging at peak, proposes plan to charge at 1 AM
4. Send: `تمام` → Agent creates plan, promises to check in 7 days
5. Send: `كيف ماشية الخطة؟` → Agent reports progress

**Demo 2: The Bill Shocked User (سارة)**
1. Send from different number: `مرحبا، فاتورتي تضاعفت بالصيف` → Agent checks data, finds AC pattern
2. Send: `المكيف بشغله على 20 درجة من الساعة 2` → Agent creates plan: raise to 24°C, pre-cool during off-peak

**Demo 3: English User (عمر)**
1. Send: `Hi, how much am I spending?` → Agent responds in English with consumption summary
2. Send: `How can I save money?` → Agent analyzes patterns, gives tips

---

## Appendix A: Seed Data Profiles

| # | Name | Phone | Subscription | Profile | Key Pattern |
|---|------|-------|-------------|---------|-------------|
| 1 | أحمد الخالدي | +962791000001 | 01-100001-01 | ev_peak_charger | 7 kW spike 7-11 PM weekdays (EV charging) |
| 2 | سارة المصري | +962791000002 | 01-100002-01 | ac_heavy_summer | 3.5 kW afternoon/evening in summer (AC) |
| 3 | محمد العبادي | +962791000003 | 01-100003-01 | water_heater_peak | 2.5 kW spike 6-8 PM daily (water heater) |
| 4 | لينا حداد | +962791000004 | 01-100004-01 | baseline_creep | 10% monthly increase over 3 months |
| 5 | عمر الزعبي | +962791000005 | 01-100005-01 | efficient_user | Low peak usage, EV charges at night |

---

## Appendix B: TOU Tariff Reference

### TOU Periods (EMRC, effective July 2025)
| Period | Hours | EV Home (fils/kWh) | EV Public (fils/kWh) |
|--------|-------|---------------------|----------------------|
| Off-Peak | 05:00-14:00 | 108 | 103 |
| Partial Peak | 14:00-17:00, 23:00-05:00 | 118 | 113 |
| Peak | 17:00-23:00 | 160 | 133 |

### Residential Tiers (JEPCO)
| Tier | kWh Range | Rate (fils/kWh) |
|------|-----------|-----------------|
| 1 | 0-160 | 33 |
| 2 | 161-320 | 72 |
| 3 | 321-480 | 86 |
| 4 | 481-640 | 114 |
| 5 | 641-800 | 158 |
| 6 | 801-1000 | 200 |
| 7 | 1000+ | 265 |

### Key Conversions
- 1 JOD = 1000 fils
- Timezone: Asia/Amman (UTC+3, no DST)
- All monetary values stored as **integer fils** in the database

---

## Appendix C: Arabic Message Templates

### Onboarding
```
مرحباً بك في كهرباءAI — محقق الطاقة الذكي! ⚡🔍

أنا مساعدك الشخصي لفهم استهلاكك للكهربا وتوفير فاتورتك.

عشان أبدأ، أعطيني رقم اشتراكك بشركة الكهرباء (JEPCO).
بتلاقيه على فاتورتك، شكله هيك: 01-XXXXXX-XX
```

### Registration Success
```
تم تسجيلك بنجاح! ✅
رقم الاشتراك: {subscription_number}

هلأ اسألني أي سؤال عن استهلاكك أو فاتورتك. مثلاً:
• ليش فاتورتي غالية؟
• شو استهلاكي هالأسبوع؟
• كيف أوفر؟
```

### Spike Detection (Proactive)
```
⚠️ تنبيه استهلاك!

لاحظت ارتفاع غير عادي: {power_kw} كيلوواط الساعة {time}
هذا {factor}x أعلى من المعتاد.

شو كان مشغل عندك هالوقت؟
```

### Plan Created
```
✅ تم إنشاء خطة التوفير!

📋 الخطة: {plan_summary}
📅 فترة المراقبة: {days} أيام
💰 التوفير المتوقع: ~{savings} دينار/شهر

رح أتابع معك وأخبرك بالنتائج بعد {days} يوم. 
اسألني "كيف ماشية الخطة؟" بأي وقت!
```

### Plan Verification (Positive)
```
📋 نتائج خطتك!

الخطة: {plan_summary}
✅ استهلاكك نزل {percent}%!
💰 توفير شهري تقريبي: {savings} دينار

ممتاز! كمّل على هالنظام 💪
```

### Error / Fallback
```
عذراً، في مشكلة تقنية حالياً. حاول مرة ثانية بعد شوي. 🔧
```

---

*End of PRD. Build one phase at a time. Test each phase before moving on.*

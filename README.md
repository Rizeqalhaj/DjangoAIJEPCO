# KahrabaAI - Smart Energy Detective

A WhatsApp AI agent that acts as a **personal energy detective** for JEPCO electricity subscribers in Jordan. It reads smart meter data, detects unusual consumption patterns, collaborates with users to investigate causes, creates optimization plans, and verifies results.

## Core Loop

```
DETECT -> INVESTIGATE -> PLAN -> VERIFY -> REPEAT
```

1. **DETECT** - Analyze 15-min interval smart meter data. Find spikes, trends, anomalies
2. **INVESTIGATE** - Show the user what the data says and ask what might be causing it
3. **PLAN** - Create actionable plans based on user input + TOU tariff optimization
4. **VERIFY** - Check meter data after monitoring period. Report savings with proof

## Key Features

- **WhatsApp Integration** - Full Twilio-powered WhatsApp bot with voice message transcription
- **Bilingual AI Agent** - Responds in Arabic (Jordanian dialect) or English based on user language
- **18 AI Tools** - Consumption analysis, spike detection, pattern recognition, bill forecasting, plan management, long-term memory
- **Smart Meter Analysis** - 15-minute interval readings with TOU period classification (Peak/Off-Peak/Partial Peak)
- **Optimization Plans** - Create, monitor, and verify energy-saving plans with baseline comparison
- **Post-Response Guardrails** - Catches LLM hallucinations (wrong data, unsaved plans, language mixing) before reaching users
- **Subscriber Notes** - Long-term memory across sessions (appliances, schedules, goals)
- **Next.js Dashboard** - Interactive charts, consumption trends, spike visualization, plan management
- **Voice Messages** - Gemini-powered transcription of WhatsApp audio messages

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.12, Django 5.x + DRF |
| LLM | Gemini 2.0 Flash via OpenAI-compatible API |
| WhatsApp | Twilio API |
| Frontend | Next.js 14, React, TypeScript, Tailwind CSS |
| Charts | Recharts |
| Database | SQLite (development) |
| Cache | Django LocMemCache (auto-detects Redis when available) |

## Project Structure

```
DjangoAIJEPCO/
├── accounts/          # Subscriber model + admin
├── meter/             # Smart meter data, analyzer, synthetic data generator
├── tariff/            # JEPCO TOU tariff engine
├── agent/             # AI agent: coach, tools, prompts, guardrails, conversation state
├── plans/             # Optimization plans + checkpoints
├── whatsapp/          # Twilio webhook, sender, voice transcription
├── notifications/     # Scheduled reports, spike alerts, plan verification
├── rag/               # Knowledge retrieval (energy tips)
├── core/              # LLM client, clock utility, debug views
├── seed/              # Demo data management commands
├── tests/             # 373 tests across 10 test files
└── frontend/          # Next.js dashboard application
```

## Quick Start

```bash
# Clone and setup
git clone https://github.com/Rizeqalhaj/DjangoAIJEPCO.git
cd DjangoAIJEPCO

# Virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Environment variables
cp .env.example .env
# Edit .env: add DJANGO_SECRET_KEY, GEMINI_API_KEY, Twilio credentials

# Database setup
python manage.py migrate
python manage.py seed_demo      # 5 demo subscribers + 30 days of readings
python manage.py seed_washer    # Optional: subscriber #6 with washing machine pattern

# Run tests
python manage.py test           # 373 tests, all passing

# Start backend
python manage.py runserver

# Start frontend (separate terminal)
cd frontend
npm install
npm run dev
```

### Getting a Gemini API Key

1. Go to https://aistudio.google.com/apikey
2. Create an API key
3. Add to `.env` as `GEMINI_API_KEY=...`

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health/` | Health check |
| GET | `/api/meter/<phone>/summary/` | Consumption summary |
| GET | `/api/meter/<phone>/daily/` | Daily breakdown |
| GET | `/api/meter/<phone>/spikes/` | Spike detection |
| GET | `/api/meter/<phone>/hourly-profile/` | Hourly consumption profile |
| GET | `/api/meter/<phone>/forecast/` | Bill forecast |
| GET | `/api/tariff/current/` | Current TOU period |
| POST | `/api/tariff/calculate/` | Calculate bill |
| POST | `/api/agent/chat/` | Agent chat |
| POST | `/api/whatsapp/webhook/` | Twilio WhatsApp webhook |
| GET | `/api/plans/<sub_number>/` | List subscriber plans |

## Demo Subscribers

| Phone | Profile | Meter |
|-------|---------|-------|
| +962791000001 | Residential family | 3-phase |
| +962791000002 | EV owner (night charging) | 3-phase |
| +962791000003 | Elderly couple | 1-phase |
| +962791000004 | Home office worker | 1-phase |
| +962791000005 | Wasteful teenager | 1-phase |
| +962791000006 | Washing machine pattern (daily 8-9pm spike) | 1-phase |

## How the AI Agent Works

The agent (`agent/coach.py`) follows a tool-use loop:

1. **Intent Classification** - Fast model classifies user intent (consumption query, plan management, greeting, etc.)
2. **Language Detection** - Determines Arabic vs English from message content
3. **Tool Execution Loop** - LLM calls tools (up to 10 iterations), executes them, feeds results back
4. **Guardrail Validation** - Post-response checks catch hallucinations and force corrections
5. **Conversation Persistence** - State saved to cache + database for cross-session continuity

### Agent Tools

The agent has 18 tools including: `get_subscriber_info`, `get_consumption_summary`, `get_daily_detail`, `detect_spikes`, `detect_patterns`, `compare_periods`, `get_bill_forecast`, `calculate_bill`, `get_tou_period`, `search_knowledge`, `create_plan`, `get_active_plan`, `get_all_plans`, `check_plan_progress`, `delete_plan`, `save_note`, `get_notes`, `update_note`

### TOU Schedule (JEPCO)

| Period | Hours | Rate |
|--------|-------|------|
| Off-Peak | 05:00 - 14:00 | Cheapest |
| Partial Peak | 14:00 - 17:00 & 23:00 - 05:00 | Mid-price |
| Peak | 17:00 - 23:00 | Most expensive |

## Dashboard

The Next.js dashboard provides:

- **KPI Cards** - Total consumption, daily average, trend, peak share
- **Daily Consumption Chart** - Stacked bar chart with TOU period breakdown
- **Hourly Profile** - Area chart showing average consumption by hour with TOU zone shading
- **TOU Breakdown Pie** - Peak vs off-peak vs partial peak distribution
- **Spike Detection** - Timeline chart with configurable date ranges (7/14/30/60/90 days + custom)
- **Plan Management** - View, verify, and cancel optimization plans
- **AI Chat** - Full chat interface with markdown rendering and quick action buttons
- **Bill Forecast** - Projected monthly consumption and cost

## Tests

```bash
python manage.py test                          # All 373 tests
python manage.py test tests.test_phase1        # Foundation (33)
python manage.py test tests.test_phase2        # Meter data layer (28)
python manage.py test tests.test_phase3        # AI agent core (53)
python manage.py test tests.test_phase4        # WhatsApp integration (56)
python manage.py test tests.test_phase5        # Plans & notifications (66)
python manage.py test tests.test_phase6        # Dashboard & polish (44)
```

All LLM calls are mocked in tests - no API key needed to run the test suite.

## Architecture Highlights

- **Gemini via OpenAI SDK** - Uses OpenAI-compatible endpoint for tool-use with Gemini models
- **Post-Response Guardrails** - Programmatic validation catches language mixing, missing tool calls, unsaved plans, and forces LLM correction before the response reaches the user
- **Spike Summarization** - Tool responses strip raw data when 3+ spikes detected, forcing the LLM to present pattern summaries instead of listing every spike
- **Persistent Conversations** - Cache + database fallback ensures conversation continuity across server restarts
- **Time-Travel Testing** - `core/clock.py` provides date override support for testing plan verification flows
- **Bilingual System Prompt** - Language instruction positioning (before vs after prompt) controls LLM output language

## License

This project is for educational and demonstration purposes.

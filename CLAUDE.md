# CLAUDE.md — KahrabaAI Project Context

## What is this project?

KahrabaAI is a WhatsApp AI agent that acts as a **personal energy detective** for JEPCO electricity subscribers in Jordan. It reads smart meter data, detects unusual consumption patterns, collaborates with the user to investigate causes, creates optimization plans, and verifies results.

Core loop: **DETECT -> INVESTIGATE -> PLAN -> VERIFY -> REPEAT**

The full PRD is in `KahrabaAI_Smart_Energy_Detective_PRD.md` at the project root.

---

## Current Phase Status

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1: Foundation | COMPLETE | Django project, models, admin, health check, 33 tests |
| Phase 2: Smart Meter Data Layer | COMPLETE | Tariff engine, meter analyzer, data generator, seed command, REST APIs, 84 tests |
| Phase 3: AI Agent Core | COMPLETE | LLM client, intent classifier, 13 agent tools, tool-use loop, conversation state, RAG stub, 41 tests |
| Phase 4: WhatsApp Integration | NOT STARTED | Meta WhatsApp Business Cloud API integration |
| Phase 5: Investigation & Plan Engine | NOT STARTED | ChromaDB RAG, enhanced investigation flows |
| Phase 6: Polish & Demo | NOT STARTED | Final polish, demo mode |

**Total tests: 158 (all passing)**

---

## Tech Stack (actual, not PRD)

- **Python 3.14** on Windows
- **Django 5.x + DRF** — web framework
- **SQLite** — database (no Docker/PostgreSQL set up yet)
- **Groq SDK** — LLM provider (NOT Anthropic/Claude — switched to free Groq LLaMA for development)
  - Main model: `llama-3.3-70b-versatile` (agent reasoning, tool use)
  - Fast model: `llama-3.1-8b-instant` (intent classification)
- **Django LocMemCache** — conversation state (no Redis available, falls back automatically)
- **No Docker, no Redis, no Celery running** — pure local dev on Windows

---

## Key Architecture Decisions

### LLM Integration (Groq, not Claude)
The PRD says Claude/Anthropic, but we switched to **Groq** for free development. The LLM client at `core/llm_client.py` uses the Groq SDK with OpenAI-compatible tool calling format. All tool definitions use `{"type": "function", "function": {...}}` format (NOT Anthropic's `input_schema` format).

### Conversation State
Uses Django's cache framework (`agent/conversation.py`). On this machine it falls back to LocMemCache (in-memory, lost on server restart). When Redis is available, it auto-detects and uses RedisCache.

### RAG Stub
`rag/retriever.py` has 10 hardcoded energy tips with keyword search. Phase 5 replaces this with ChromaDB vector search.

### SQLite timezone fix
`meter/analyzer.py` has a critical fix: `ExtractHour` returns UTC hour on SQLite, so we add `tzinfo=JORDAN_TZ` to datetime objects. Spike detection tests use dates relative to `timezone.now()` (not fixed dates) to avoid timezone issues.

---

## Project Structure

```
KahrabaAIDjango/
├── config/              # Django project settings
│   ├── settings.py      # Main config (Groq key, cache, logging)
│   ├── urls.py          # Root URL conf
│   ├── celery.py        # Celery config (not active)
│   └── wsgi.py / asgi.py
├── accounts/            # Subscriber model + admin
│   ├── models.py        # Subscriber (phone, subscription_number, meter_type, etc.)
│   └── admin.py
├── meter/               # Smart meter data
│   ├── models.py        # MeterReading (15-min intervals, kWh, power_kw, tou_period)
│   ├── analyzer.py      # MeterAnalyzer: summary, daily, spikes, patterns, forecast
│   ├── generator.py     # Synthetic data generator (5 profiles)
│   ├── serializers.py   # DRF serializers
│   ├── urls.py          # /api/meter/<phone>/summary|daily|spikes|forecast
│   └── views.py         # API views
├── tariff/              # JEPCO tariff engine
│   ├── engine.py        # TariffEngine: calculate_bill, get_tou_period, estimate_cost
│   ├── urls.py          # /api/tariff/current|calculate
│   └── views.py
├── agent/               # AI Agent (Phase 3)
│   ├── coach.py         # EnergyDetective: main agent class with tool-use loop
│   ├── intent.py        # Intent classifier (7 intents, uses fast model)
│   ├── prompts.py       # System prompt (bilingual Arabic/English)
│   ├── tools.py         # 13 tool definitions (OpenAI format) + execute_tool()
│   ├── conversation.py  # ConversationManager (Django cache, 30-min TTL)
│   ├── urls.py          # /api/agent/chat/
│   └── views.py         # AgentChatView (POST)
├── plans/               # Optimization plans
│   ├── models.py        # OptimizationPlan, PlanCheckpoint
│   └── services.py      # create_optimization_plan, get_active_plan, check_progress
├── rag/                 # Knowledge retrieval
│   ├── retriever.py     # Stub: 10 hardcoded tips with keyword search
│   └── documents/       # Empty (Phase 5 adds real documents)
├── core/                # Shared utilities
│   └── llm_client.py    # Groq SDK wrapper (chat_with_tools, classify_fast)
├── seed/                # Demo data
│   └── management/commands/seed_demo.py  # Creates 5 subscribers + 30 days of readings
├── whatsapp/            # Phase 4 (skeleton)
├── notifications/       # Phase 6 (skeleton)
├── tests/               # All tests
│   ├── test_phase1.py   # 33 tests (models, admin, health check)
│   ├── test_phase2.py   # 84 tests (tariff, meter, seed, APIs)
│   ├── test_phase3.py   # 41 tests (LLM client, intent, tools, agent, RAG)
│   ├── test_tariff_engine.py
│   └── test_meter_analyzer.py
├── .env.example         # Template — copy to .env and fill in keys
├── requirements.txt     # Python dependencies
├── manage.py
├── Dockerfile           # Not actively used
└── docker-compose.yml   # Not actively used
```

---

## How to Set Up on a New Machine

```bash
# 1. Clone the repo
git clone <repo-url>
cd KahrabaAIDjango

# 2. Create virtual environment
python -m venv venv

# 3. Activate (Windows)
venv\Scripts\activate
# Or (Linux/Mac)
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Copy environment template and fill in your keys
cp .env.example .env
# Edit .env: add DJANGO_SECRET_KEY (any random string) and GROQ_API_KEY

# 6. Run migrations
python manage.py migrate

# 7. Seed demo data (5 subscribers, 30 days of meter readings)
python manage.py seed_demo

# 8. Run tests (all 158 should pass)
python manage.py test

# 9. Start dev server
python manage.py runserver
```

### Getting a Groq API Key
1. Go to https://console.groq.com
2. Sign up (free)
3. Create an API key
4. Add it to `.env` as `GROQ_API_KEY=gsk_...`
5. Free tier: 100K tokens/day, which is enough for testing

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health/` | Health check |
| GET | `/api/meter/<phone>/summary/` | Consumption summary (30 days) |
| GET | `/api/meter/<phone>/daily/?date=YYYY-MM-DD` | Daily breakdown |
| GET | `/api/meter/<phone>/spikes/` | Spike detection |
| GET | `/api/meter/<phone>/forecast/` | Bill forecast |
| GET | `/api/tariff/current/` | Current TOU period |
| POST | `/api/tariff/calculate/` | Calculate bill `{"kwh": 500}` |
| POST | `/api/agent/chat/` | Agent chat `{"phone": "+962791000001", "message": "..."}` |

---

## Demo Subscriber Phones

| Phone | Profile | Meter |
|-------|---------|-------|
| +962791000001 | Residential family | 3-phase |
| +962791000002 | EV owner (night charging) | 3-phase |
| +962791000003 | Elderly couple | 1-phase |
| +962791000004 | Home office worker | 1-phase |
| +962791000005 | Wasteful teenager | 1-phase |

---

## Running Tests

```bash
# All tests
python manage.py test

# Specific phase
python manage.py test tests.test_phase1
python manage.py test tests.test_phase2
python manage.py test tests.test_phase3

# Specific test class
python manage.py test tests.test_phase3.ToolExecutionTest
```

---

## Important Notes

- The Groq free tier has a 100K tokens/day limit. If you hit rate limits, wait ~30 min or upgrade.
- The agent chat endpoint can take 5-30 seconds to respond (multiple LLM calls for intent + reasoning + tools).
- All LLM calls are mocked in tests — no API key needed to run tests.
- The system prompt in `agent/prompts.py` is bilingual (Arabic/English) and designed for WhatsApp-style concise messages.
- The agent has 13 tools it can call. Tool definitions are in OpenAI format in `agent/tools.py`.

---

## Next Phase to Implement

**Phase 4: WhatsApp Integration** — see `KahrabaAI_Smart_Energy_Detective_PRD.md` for full specs. Key tasks:
- Meta WhatsApp Business Cloud API webhook
- Message receive/send handlers
- Message templates for Arabic
- Celery async processing (requires Redis)

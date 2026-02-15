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
| Phase 3: AI Agent Core | COMPLETE | LLM client, intent classifier, 14 agent tools, tool-use loop, conversation state, RAG stub, guardrails, 53 tests |
| Phase 4: WhatsApp Integration | COMPLETE | Twilio WhatsApp API, webhook, sender, Celery fallback, onboarding, message splitting, 56 tests |
| Phase 5: Investigation & Plan Engine | PARTIAL | Notifications, plan verification, delete_plan, scheduled tasks, knowledge ingestion, 66 tests |
| Phase 6: Polish & Demo | PARTIAL | Time-travel testing, edge case fixes, dynamic language, dashboard, custom date ranges, 44 tests |

**Total tests: 336 (all passing)**

---

## Tech Stack (actual, not PRD)

- **Python 3.12** on Linux (Ubuntu)
- **Django 5.x + DRF** — web framework
- **SQLite** — database (no Docker/PostgreSQL set up yet)
- **Gemini** — LLM provider via OpenAI-compatible endpoint
  - Main model: `gemini-2.0-flash` (agent reasoning, tool use)
  - Fast model: `gemini-2.0-flash` (intent classification)
  - Base URL: `https://generativelanguage.googleapis.com/v1beta/openai/`
  - API key in `.env` as `GEMINI_API_KEY`
- **Twilio** — WhatsApp integration (real messages, not dry-run)
- **Django LocMemCache** — conversation state (no Redis available, falls back automatically)
- **No Docker, no Redis, no Celery running** — pure local dev

---

## Key Architecture Decisions

### LLM Integration (Gemini via OpenAI-compatible endpoint)
The LLM client at `core/llm_client.py` uses the OpenAI SDK pointed at Gemini's endpoint. All tool definitions use `{"type": "function", "function": {...}}` format (OpenAI-compatible, NOT Anthropic's `input_schema` format).

### Conversation State
Uses Django's cache framework (`agent/conversation.py`). On this machine it falls back to LocMemCache (in-memory, lost on server restart). When Redis is available, it auto-detects and uses RedisCache.

### RAG Stub
`rag/retriever.py` has 10 hardcoded energy tips with keyword search. Phase 5 replaces this with ChromaDB vector search.

### SQLite timezone fix
`meter/analyzer.py` has a critical fix: `ExtractHour` returns UTC hour on SQLite, so we add `tzinfo=JORDAN_TZ` to datetime objects. Spike detection tests use dates relative to `timezone.now()` (not fixed dates) to avoid timezone issues.

### Post-Response Guardrails (`agent/guardrails.py`)
Programmatic validation layer that runs AFTER the LLM responds but BEFORE sending to the user. Catches common LLM misbehaviors:
1. **Language mixing** — detects Arabic chars in English responses (or excessive English in Arabic)
2. **Tool usage** — detects data questions answered without calling any tools
3. **Plan creation** — detects plan descriptions in text without a `create_plan` tool call
4. **Plan deletion** — detects user asking to cancel/delete a plan but agent not calling `delete_plan` tool (skips if `get_active_plan` was called, meaning agent checked first)

Arabic plan-creation regex uses specific phrases (خطة التوفير, خطة تحسين, etc.) rather than broad `خطة` to avoid false positives when merely referencing existing plans. User-delete patterns require "plan" context to avoid triggering on unrelated "cancel"/"remove" requests.

When high-severity violations are detected, `coach.py` automatically injects a correction prompt, re-calls the LLM, runs any triggered tool calls, and strips the correction exchange from the conversation cache so it's invisible to future turns.

### Custom Date Range Support
`meter/analyzer.py` `get_consumption_summary()` accepts optional `start_date`/`end_date` for exact calendar month queries (e.g. "January 2026" → `2026-01-01` to `2026-01-31`). The `days` parameter is for rolling windows only. Backend API views and frontend hooks also support `?start_date=&end_date=` query params. The dashboard has a "Custom" date range picker alongside preset day buttons.

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
│   ├── coach.py         # EnergyDetective: main agent class with tool-use loop + guardrail integration
│   ├── guardrails.py    # Post-response validation (language mixing, tool usage, plan creation/deletion)
│   ├── intent.py        # Intent classifier (7 intents incl. plan_management, uses fast model)
│   ├── prompts.py       # System prompt (bilingual Arabic/English)
│   ├── tools.py         # 14 tool definitions (OpenAI format) + execute_tool()
│   ├── conversation.py  # ConversationManager (Django cache, 30-min TTL)
│   ├── urls.py          # /api/agent/chat/
│   └── views.py         # AgentChatView (POST)
├── plans/               # Optimization plans
│   ├── models.py        # OptimizationPlan, PlanCheckpoint
│   ├── services.py      # create_optimization_plan, get_active_plan, check_progress, delete_plan
│   ├── urls.py          # /api/plans/<sub_number>/ and /api/plans/detail/<plan_id>/
│   └── views.py         # SubscriberPlansView (GET), PlanDetailView (DELETE)
├── rag/                 # Knowledge retrieval
│   ├── retriever.py     # Stub: 10 hardcoded tips with keyword search
│   └── documents/       # Empty (Phase 5 adds real documents)
├── core/                # Shared utilities
│   ├── llm_client.py    # Gemini via OpenAI SDK (chat_with_tools, classify_fast)
│   ├── clock.py         # Time utility with override support for time-travel testing
│   ├── debug_views.py   # Debug API (time override get/set/clear)
│   └── debug_urls.py    # /api/debug/time/
├── seed/                # Demo data
│   └── management/commands/
│       ├── seed_demo.py     # Creates 5 subscribers + 30 days of readings
│       └── seed_washer.py   # Creates subscriber #6 (washing machine pattern, 90 days)
├── whatsapp/            # WhatsApp Integration (Phase 4 — Twilio)
│   ├── webhook.py       # Twilio POST webhook, X-Twilio-Signature verification
│   ├── sender.py        # Twilio SDK client (send_text, send_buttons, send_list)
│   ├── tasks.py         # Message processing, Celery/sync fallback, registration, splitting
│   ├── message_templates.py  # Arabic/English message templates
│   └── urls.py          # /api/whatsapp/webhook/
├── notifications/       # Scheduled notifications (weekly reports, spike alerts, plan verification)
│   ├── tasks.py         # send_weekly_reports, send_spike_alerts, check_plan_verifications
│   ├── views.py         # NotificationTriggerView (POST, staff-only)
│   ├── urls.py          # /api/notifications/trigger/
│   ├── message_templates.py  # All notification templates (AR/EN)
│   └── management/commands/  # ingest_knowledge, send_notifications
├── tests/               # All tests
│   ├── test_phase1.py   # 33 tests (models, admin, health check)
│   ├── test_phase2.py   # 28 tests (meter, seed, APIs)
│   ├── test_phase3.py   # 53 tests (LLM client, intent, tools, agent, RAG, guardrails)
│   ├── test_phase4.py   # 56 tests (Twilio webhook, sender, tasks, registration, edge cases)
│   ├── test_phase5.py   # 66 tests (notifications, plan services, agent edge cases)
│   ├── test_phase6.py   # 44 tests (dashboard, time-travel, custom date ranges)
│   ├── test_tariff_engine.py  # Tariff engine unit tests
│   └── test_meter_analyzer.py # Meter analyzer unit tests
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
# Edit .env: add DJANGO_SECRET_KEY, GEMINI_API_KEY, and Twilio creds

# 6. Run migrations
python manage.py migrate

# 7. Seed demo data (5 subscribers + 30 days of readings)
python manage.py seed_demo
# Optional: subscriber #6 with washing machine pattern (90 days)
python manage.py seed_washer

# 8. Run tests (all 336 should pass)
python manage.py test

# 9. Start dev server
python manage.py runserver
```

### Getting a Gemini API Key
1. Go to https://aistudio.google.com/apikey
2. Create an API key
3. Add it to `.env` as `GEMINI_API_KEY=...`

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health/` | Health check |
| GET | `/api/meter/<phone>/summary/` | Consumption summary (30 days default, supports `?start_date=&end_date=`) |
| GET | `/api/meter/<phone>/daily/?date=YYYY-MM-DD` | Daily breakdown (also supports `?start_date=&end_date=` for series) |
| GET | `/api/meter/<phone>/spikes/` | Spike detection |
| GET | `/api/meter/<phone>/forecast/` | Bill forecast |
| GET | `/api/tariff/current/` | Current TOU period |
| POST | `/api/tariff/calculate/` | Calculate bill `{"kwh": 500}` |
| POST | `/api/agent/chat/` | Agent chat `{"phone": "+962791000001", "message": "..."}` |
| POST | `/api/whatsapp/webhook/` | Twilio WhatsApp webhook (X-Twilio-Signature verified) |
| GET | `/api/plans/<sub_number>/` | List subscriber's plans |
| DELETE | `/api/plans/detail/<plan_id>/` | Delete a plan |
| POST | `/api/notifications/trigger/` | Trigger notifications (staff-only) |
| GET/POST/DELETE | `/api/debug/time/` | Time-travel override (get/set/clear) |

---

## Demo Subscriber Phones

| Phone | Profile | Meter |
|-------|---------|-------|
| +962791000001 | Residential family | 3-phase |
| +962791000002 | EV owner (night charging) | 3-phase |
| +962791000003 | Elderly couple | 1-phase |
| +962791000004 | Home office worker | 1-phase |
| +962791000005 | Wasteful teenager | 1-phase |
| +962791000006 | Washing machine pattern (daily 8-9pm spike) | 1-phase |

---

## Running Tests

```bash
# All tests
python manage.py test

# Specific phase
python manage.py test tests.test_phase1
python manage.py test tests.test_phase2
python manage.py test tests.test_phase3
python manage.py test tests.test_phase4
python manage.py test tests.test_phase5
python manage.py test tests.test_phase6

# Specific test class
python manage.py test tests.test_phase3.ToolExecutionTest
```

---

## Important Notes

- The agent chat endpoint can take 5-30 seconds to respond (multiple LLM calls for intent + reasoning + tools).
- All LLM calls are mocked in tests — no API key needed to run tests.
- The system prompt in `agent/prompts.py` is bilingual (Arabic/English) and designed for WhatsApp-style concise messages.
- The agent has 14 tools it can call. Tool definitions are in OpenAI format in `agent/tools.py`.
- Post-response guardrails (`agent/guardrails.py`) catch language mixing, missing tool calls, unsaved plans, and undeleted plans before responses reach the user.
- Subscriber ID 1 phone was changed to `+962798494038` for live WhatsApp testing.
- Subscriber #6 (+962791000006, رنا الحسيني) has a washing machine pattern: 2kW spike at 20:00-21:00 daily for 90 days. Created via `python manage.py seed_washer`.
- Data range for subscriber 1: 2025-11-12 to 2026-02-10 (no data after Feb 10).
- Dashboard supports custom date range filtering with `start_date`/`end_date` query params on summary and daily series endpoints.

---

## Known Issues & Lessons Learned (IMPORTANT)

### 1. Gemini requires `name` field on tool responses
**Problem:** Gemini's OpenAI-compatible API requires `"name": "<tool_name>"` on every tool response message. Without it, you get `function_response.name: Name cannot be empty` (400 error).
**Fix:** Always include `"name": tc.function.name` when appending tool results to history in `agent/coach.py`. Also sanitize cached conversation history to strip old tool messages that lack the `name` field.
**Files:** `agent/coach.py` (tool response append + history sanitizer)

### 2. LLM hallucination — data from memory instead of calling tools
**Problem:** The LLM sometimes answers data questions from conversation context or memory instead of calling tools, reporting invented numbers (e.g. "13.9 kWh" when no data exists).
**Fix:** System prompt rule #3 explicitly mandates calling a tool for EVERY data question, even if similar data appeared earlier. Rule #8 mandates reporting "no data" when `no_data: true` is returned by a tool.
**Files:** `agent/prompts.py` (rules 3 and 8), `meter/analyzer.py` (`no_data: true` flag in `get_daily_summary`)

### 3. LLM hallucination — wrong TOU tariff times
**Problem:** The LLM invented wrong TOU periods (e.g. "off-peak: 7 PM to 6 AM" when off-peak is actually 05:00–14:00). This led to dangerous advice telling users to use more electricity during PEAK hours.
**Fix:** Baked the correct TOU schedule directly into the system prompt so the LLM cannot hallucinate different times. Also added `full_schedule` to `get_tou_period()` tool response.
**Files:** `agent/prompts.py` (## TOU Schedule section), `tariff/engine.py` (`full_schedule` in response)

### 4. Response truncation (max_tokens too low)
**Problem:** Long agent responses (especially plan descriptions) got cut off mid-sentence because `max_tokens=1024` was too small.
**Fix:** Increased to `max_tokens=2048` in `agent/coach.py`.

### 5. LLM cannot compute relative dates without knowing "today"
**Problem:** When user asks "show me yesterday" or "compare this week vs last week", the LLM doesn't know the current date and either guesses wrong or asks the user for explicit dates.
**Fix:** Inject current date/time from `core.clock.now()` into the system prompt. This also respects time-travel overrides.
**Files:** `agent/coach.py` (## Current Date & Time section in system prompt)

### 6. Mixed language detection
**Problem:** For messages mixing Arabic and English (e.g. "I want to know عن استهلاكي"), the intent classifier defaulted to Arabic, causing the agent to respond in the wrong language.
**Fix:** Added explicit language detection rules to the intent classifier prompt: detect based on sentence frame/structure language.
**Files:** `agent/intent.py` (Language detection rules section)

### 7. Conversation cache corruption across turns
**Problem:** Cached conversation history accumulates tool call/response messages from previous turns. When sent back to the API, these messages may be missing required fields (like `name`), causing API errors.
**Fix:** History sanitizer in `_run_tool_loop()` strips tool-related messages from cached history before the first API call. Within the current turn's tool loop, new messages are properly formed.
**Files:** `agent/coach.py` (sanitizer block before first `chat_with_tools` call)

### 8. First message always in Arabic regardless of user language
**Problem:** When an English-speaking user sends their first message, the agent responds in Arabic. The language instruction was appended AFTER the Arabic-heavy system prompt, so the LLM saw Arabic first and defaulted to it.
**Fix:** Prepend the language instruction BEFORE the system prompt for English users. For Arabic users, append it after. What the LLM sees first dominates its output language.
**Files:** `agent/coach.py` (`_run_tool_loop()` — language-dependent system prompt construction)

### 9. Language mixing in multi-turn responses
**Problem:** Agent correctly responds in English for the first message but switches to Arabic for follow-up questions. Root cause: Arabic-only example phrases in the system prompt (e.g. `"بشوف ارتفاع كل يوم..."`) were being copied verbatim as templates.
**Fix:** Rewrote system prompt to be English-first with bilingual examples. Strengthened language rule to "HIGHEST PRIORITY" with explicit "not even a single word or phrase" phrasing. Added programmatic guardrails as a safety net.
**Files:** `agent/prompts.py` (bilingual examples), `agent/coach.py` (language rule positioning), `agent/guardrails.py` (language mixing detection)

### 10. Plans described in text but never saved to database
**Problem:** When the user asks to create a plan, the LLM describes the plan in text but never calls the `create_plan` tool, so 0 plans exist in the database and nothing shows on the dashboard.
**Fix:** Rewrote system prompt rule #6 to explicitly state "A plan does NOT exist until you call create_plan — describing it in text is not enough." Added `check_plan_saved()` guardrail that detects plan descriptions without a matching `create_plan` tool call, and auto-corrects by re-prompting the LLM.
**Files:** `agent/prompts.py` (rule #6), `agent/tools.py` (tool description), `agent/guardrails.py` (`check_plan_saved`), `agent/coach.py` (guardrail integration)

### 11. Monthly queries using wrong date ranges
**Problem:** When a user asks about "January" or "last month", the agent uses the `days` parameter (rolling window) instead of exact calendar month boundaries, giving incorrect data.
**Fix:** Added `start_date`/`end_date` parameters to `get_consumption_summary` tool definition and `MeterAnalyzer`. Added explicit `## Month Queries` section in system prompt with examples. System prompt rule: "NEVER use the days parameter for month queries."
**Files:** `meter/analyzer.py`, `agent/tools.py`, `agent/prompts.py` (## Month Queries section)

### 12. Plans not deleted when user asks to cancel
**Problem:** Agent describes deleting the plan in text without actually calling the `delete_plan` tool. Same class of bug as #10 (plans described but not saved).
**Fix:** Added system prompt rule #7 mandating `delete_plan` tool calls. Added `check_plan_deleted()` guardrail with correction loop. Strengthened `delete_plan` tool description. Delete guardrail skips if `get_active_plan` was already called (agent checked first and found no plan).
**Files:** `agent/prompts.py` (rule #7), `agent/tools.py`, `agent/guardrails.py` (`check_plan_deleted`), `agent/coach.py` (correction prompt)

### 13. Arabic language rule too strict — forced translation of technical terms
**Problem:** Arabic language instruction said "Do NOT include ANY English text" which forced the LLM to awkwardly translate standard terms like kWh, JOD, JEPCO, TOU into Arabic.
**Fix:** Relaxed the rule to allow standard technical terms and units (kWh, JOD, JEPCO, TOU, AC, EV, fils, kW) while requiring all sentences to be in Arabic.
**Files:** `agent/coach.py` (Arabic language rule in `_run_tool_loop()`)

### 14. Guardrails false positives on Arabic plan references
**Problem:** The Arabic plan-creation regex used standalone `خطة` (plan) which matched any mention of "plan" — including when the agent was checking or referencing an existing plan, not creating a new one.
**Fix:** Narrowed Arabic regex to specific plan-creation phrases only (خطة التوفير, خطة تحسين, فترة المراقبة, هاي الخطة, الإجراءات التالية). Similarly, delete-check user patterns now require "plan" context.
**Files:** `agent/guardrails.py` (`_PLAN_DESCRIBED_AR`, `_USER_DELETE_EN`, `_USER_DELETE_AR`)

---

## Remaining Work

**Phase 5 (remaining):**
- ChromaDB vector search replacing RAG stub
- Document ingestion pipeline (energy tips, tariff docs)
- Celery beat scheduling for automated notifications

**Phase 6 (remaining):**
- Final polish and demo mode
- Plan abandonment/cancellation via WhatsApp agent and dashboard (plan exists at `~/.claude/plans/`)
- End-to-end demo walkthrough

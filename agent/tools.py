"""Agent tool definitions and execution (OpenAI-compatible format for Groq)."""

import json
from datetime import date as _date

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_subscriber_info",
            "description": (
                "Get subscriber details including household size, area, whether they have "
                "EV/solar, and tariff category. Call this when you need context about the user's home."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {"type": "string", "description": "Phone number in E.164 format"},
                },
                "required": ["phone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_consumption_summary",
            "description": (
                "Get overall consumption summary for the subscriber. "
                "Returns total kWh, average daily kWh, peak/off-peak split, "
                "highest/lowest day, cost estimate, and trend direction. "
                "Use start_date + end_date for a specific calendar month or date range "
                "(e.g. January 2026 = start_date 2026-01-01, end_date 2026-01-31). "
                "Use days for a rolling window (e.g. last 7 days, last 30 days). "
                "If none provided, defaults to last 30 days."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {"type": "string", "description": "Phone number"},
                    "days": {"type": "integer", "description": "Rolling window in days (default 30). Ignored if start_date/end_date provided."},
                    "start_date": {"type": "string", "description": "Start date YYYY-MM-DD (use for specific month/period queries)"},
                    "end_date": {"type": "string", "description": "End date YYYY-MM-DD (use for specific month/period queries)"},
                },
                "required": ["phone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_daily_detail",
            "description": (
                "Get detailed consumption breakdown for a specific day. "
                "Returns hourly consumption, peak/off-peak split, max power draw, "
                "and cost by TOU period."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {"type": "string", "description": "Phone number"},
                    "date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                },
                "required": ["phone", "date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "detect_spikes",
            "description": (
                "Find unusual consumption spikes. "
                "A spike is when power draw exceeds 2x the normal level for that hour. "
                "Returns timestamp, magnitude, duration, TOU period, and estimated extra cost. "
                "Use start_date/end_date when the user asks about a specific date or period. "
                "Use days=30 for general spike questions. "
                "NEVER use days=1 — use start_date/end_date for specific dates instead."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {"type": "string", "description": "Phone number"},
                    "days": {"type": "integer", "description": "Number of days back from today. Use 30 for general questions."},
                    "start_date": {"type": "string", "description": "Start date YYYY-MM-DD. Use with end_date for specific date ranges."},
                    "end_date": {"type": "string", "description": "End date YYYY-MM-DD. Use with start_date for specific date ranges."},
                },
                "required": ["phone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "detect_patterns",
            "description": (
                "Find recurring consumption patterns over the last N days. "
                "E.g., 'Every weekday at 19:00, consumption jumps to 8 kW for 4 hours.' "
                "Returns pattern details with consistency score."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {"type": "string", "description": "Phone number"},
                    "days": {"type": "integer", "description": "Number of days to analyze (default 14)"},
                },
                "required": ["phone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_periods",
            "description": (
                "Compare consumption between two time periods. "
                "Use for week-over-week or month-over-month comparisons. "
                "Returns change in kWh, cost, and percentage."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {"type": "string", "description": "Phone number"},
                    "period1_start": {"type": "string", "description": "Start date YYYY-MM-DD"},
                    "period1_end": {"type": "string", "description": "End date YYYY-MM-DD"},
                    "period2_start": {"type": "string", "description": "Start date YYYY-MM-DD"},
                    "period2_end": {"type": "string", "description": "End date YYYY-MM-DD"},
                },
                "required": ["phone", "period1_start", "period1_end", "period2_start", "period2_end"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_bill_forecast",
            "description": (
                "Predict the end-of-month electricity bill based on consumption so far "
                "this billing cycle. Returns projected kWh, projected bill in JOD, "
                "tier reached, and comparison to last month."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {"type": "string", "description": "Phone number"},
                },
                "required": ["phone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_bill",
            "description": (
                "Calculate the electricity bill for a given monthly kWh amount using "
                "JEPCO's tiered residential tariff. Returns total in JOD, tier breakdown, "
                "and average rate."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "monthly_kwh": {"type": "number", "description": "Monthly consumption in kWh"},
                },
                "required": ["monthly_kwh"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_tou_period",
            "description": (
                "Get the current Time-of-Use tariff period. Returns period name "
                "(off-peak/partial-peak/peak), rate in fils/kWh, time remaining "
                "in current period, and next period info."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": (
                "Search the knowledge base for information about tariffs, billing, "
                "energy saving tips, or JEPCO policies. Use when the user asks "
                "specific questions about rates or procedures."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query in Arabic or English"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_plan",
            "description": (
                "Create and save a new optimization plan to the database. "
                "You MUST call this tool whenever the user agrees to a plan — "
                "describing a plan in text does NOT save it. "
                "Call after: (1) you detected a pattern, (2) user confirmed the cause, "
                "(3) user agreed to the actions. The plan is only real once this tool is called."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {"type": "string", "description": "Phone number"},
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
                                "expected_savings_fils_per_day": {"type": "integer"},
                            },
                        },
                        "description": "List of specific actions",
                    },
                    "monitoring_days": {"type": "integer", "description": "Days to wait before verification (default 7)"},
                },
                "required": ["phone", "detected_pattern", "user_hypothesis", "plan_summary", "actions"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_active_plan",
            "description": (
                "Get the subscriber's current active optimization plan, if any. "
                "Returns plan details, creation date, and progress status."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {"type": "string", "description": "Phone number"},
                },
                "required": ["phone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_all_plans",
            "description": (
                "Get ALL optimization plans for the subscriber (active, monitoring, completed, abandoned). "
                "Use this when the user asks how many plans they have or wants to see their plan history."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {"type": "string", "description": "Phone number"},
                },
                "required": ["phone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_plan_progress",
            "description": (
                "Compare current consumption data against the plan's baseline to "
                "check if the plan is working. Returns baseline vs actual, "
                "percentage change, and whether the target is being met. "
                "If plan_id is not provided, checks the latest active plan automatically."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {"type": "string", "description": "Phone number"},
                    "plan_id": {"type": "integer", "description": "Plan ID (optional, defaults to active plan)"},
                },
                "required": ["phone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_plan",
            "description": (
                "Delete/cancel the subscriber's optimization plan. "
                "You MUST call this tool whenever the user wants to cancel, delete, or remove a plan — "
                "saying 'I deleted it' in text does NOT delete it. Only this tool call actually removes it. "
                "If plan_id is not provided, deletes the latest active plan."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {"type": "string", "description": "Phone number"},
                    "plan_id": {"type": "integer", "description": "Plan ID (optional, defaults to active plan)"},
                },
                "required": ["phone"],
            },
        },
    },
    # --- Notes tools (long-term memory) ---
    {
        "type": "function",
        "function": {
            "name": "save_note",
            "description": (
                "Save a learned fact about the user for long-term memory across sessions. "
                "Use when user mentions: specific appliances (water heater, AC, EV charger), "
                "daily schedule/habits, savings goals, household composition. "
                "Do NOT save trivial things (greetings) or data already in subscriber_info."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {"type": "string", "description": "Phone number"},
                    "category": {
                        "type": "string",
                        "enum": ["appliance", "schedule", "preference", "household_fact", "goal"],
                        "description": "Category of the fact",
                    },
                    "content": {"type": "string", "description": "The fact to remember, in English"},
                },
                "required": ["phone", "category", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_notes",
            "description": (
                "Get all saved notes about a subscriber. Notes are also auto-injected into "
                "your context, but use this tool to explicitly refresh if needed."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {"type": "string", "description": "Phone number"},
                },
                "required": ["phone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_note",
            "description": (
                "Update or deactivate a saved note. Use when user corrects a previous fact "
                "(e.g. 'I sold my EV') — update the content or set is_active=false to remove it."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {"type": "string", "description": "Phone number"},
                    "note_id": {"type": "integer", "description": "ID of the note to update"},
                    "content": {"type": "string", "description": "New content (optional)"},
                    "is_active": {"type": "boolean", "description": "Set to false to deactivate"},
                },
                "required": ["phone", "note_id"],
            },
        },
    },
]


def execute_tool(tool_name: str, tool_input: dict) -> str:
    """
    Execute an agent tool and return the result as a JSON string.

    Maps tool names to actual service calls.
    """
    from accounts.models import Subscriber
    from meter.analyzer import MeterAnalyzer
    from tariff.engine import get_tou_period, calculate_residential_bill
    from plans.services import (
        create_optimization_plan,
        get_active_plan,
        check_progress,
        delete_plan,
    )
    from rag.retriever import search

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
            start_date = tool_input.get("start_date")
            end_date = tool_input.get("end_date")
            if start_date and end_date:
                result = analyzer.get_consumption_summary(
                    start_date=_date.fromisoformat(start_date),
                    end_date=_date.fromisoformat(end_date),
                )
            else:
                result = analyzer.get_consumption_summary(
                    days=tool_input.get("days", 30)
                )
            return json.dumps(result, ensure_ascii=False, default=str)

        elif tool_name == "get_daily_detail":
            sub = get_sub(tool_input["phone"])
            analyzer = MeterAnalyzer(sub)
            target = _date.fromisoformat(tool_input["date"])
            result = analyzer.get_daily_summary(target)
            return json.dumps(result, ensure_ascii=False, default=str)

        elif tool_name == "detect_spikes":
            sub = get_sub(tool_input["phone"])
            analyzer = MeterAnalyzer(sub)
            start_date = tool_input.get("start_date")
            end_date = tool_input.get("end_date")
            if start_date and end_date:
                spikes = analyzer.detect_spikes(
                    start_date=_date.fromisoformat(start_date),
                    end_date=_date.fromisoformat(end_date),
                )
            else:
                spikes = analyzer.detect_spikes(days=tool_input.get("days", 30))
            # When 3+ spikes, send only a summary (no individual spike list)
            # so the LLM presents the pattern, not a dump of every spike.
            if len(spikes) >= 3:
                powers = [s["power_kw"] for s in spikes]
                hours = []
                tou_periods = set()
                total_extra_cost = 0
                dates = []
                for s in spikes:
                    try:
                        ts = s.get("timestamp", "")
                        h = int(ts[11:13]) if len(ts) >= 13 else None
                        if h is not None:
                            hours.append(h)
                        dates.append(ts[:10])
                    except (ValueError, TypeError):
                        pass
                    tou_periods.add(s.get("tou_period", ""))
                    total_extra_cost += s.get("estimated_extra_cost_fils", 0)
                common_hour = max(set(hours), key=hours.count) if hours else None
                response = {
                    "count": len(spikes),
                    "summary": (
                        f"{len(spikes)} spikes detected"
                        + (f", mostly around {common_hour}:00" if common_hour is not None else "")
                        + (f" during {'/'.join(tou_periods)} hours" if tou_periods else "")
                        + f", power range {min(powers)}-{max(powers)} kW"
                        + f", total extra cost ~{round(total_extra_cost / 1000, 2)} JOD"
                    ),
                    "date_range": f"{dates[0]} to {dates[-1]}" if dates else "",
                    "avg_power_kw": round(sum(powers) / len(powers), 2),
                    "peak_power_kw": max(powers),
                    "common_hour": f"{common_hour}:00" if common_hour is not None else None,
                    "tou_periods": list(tou_periods),
                }
            else:
                response = {"count": len(spikes), "spikes": spikes}
            return json.dumps(response, ensure_ascii=False, default=str)

        elif tool_name == "detect_patterns":
            sub = get_sub(tool_input["phone"])
            analyzer = MeterAnalyzer(sub)
            result = analyzer.detect_recurring_pattern(
                days=tool_input.get("days", 14)
            )
            return json.dumps(result, ensure_ascii=False, default=str)

        elif tool_name == "compare_periods":
            sub = get_sub(tool_input["phone"])
            analyzer = MeterAnalyzer(sub)
            result = analyzer.compare_periods(
                _date.fromisoformat(tool_input["period1_start"]),
                _date.fromisoformat(tool_input["period1_end"]),
                _date.fromisoformat(tool_input["period2_start"]),
                _date.fromisoformat(tool_input["period2_end"]),
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
                "message": "Plan saved. Will check results after monitoring period.",
            }, ensure_ascii=False)

        elif tool_name == "get_active_plan":
            sub = get_sub(tool_input["phone"])
            plan = get_active_plan(sub)
            if plan:
                return json.dumps({
                    "plan_id": plan.id,
                    "summary": plan.plan_summary,
                    "status": plan.status,
                    "created_on": str(plan.created_at.date()),
                    "verify_after": str(plan.verify_after_date),
                    "user_hypothesis": plan.user_hypothesis,
                    "actions": plan.plan_details.get("actions", []),
                    "_note": "created_on is the actual date this plan was saved. Report this exact date.",
                }, ensure_ascii=False)
            return json.dumps({"plan": None, "message": "No active plan"})

        elif tool_name == "get_all_plans":
            from plans.services import get_all_plans
            sub = get_sub(tool_input["phone"])
            plans = get_all_plans(sub)
            return json.dumps({
                "total": len(plans),
                "plans": plans,
            }, ensure_ascii=False)

        elif tool_name == "check_plan_progress":
            sub = get_sub(tool_input["phone"])
            result = check_progress(sub, tool_input.get("plan_id"))
            return json.dumps(result, ensure_ascii=False, default=str)

        elif tool_name == "delete_plan":
            sub = get_sub(tool_input["phone"])
            result = delete_plan(sub, tool_input.get("plan_id"))
            return json.dumps(result, ensure_ascii=False, default=str)

        elif tool_name == "save_note":
            from agent.notes_service import save_note as svc_save_note
            sub = get_sub(tool_input["phone"])
            note = svc_save_note(
                subscriber=sub,
                category=tool_input["category"],
                content=tool_input["content"],
            )
            return json.dumps({
                "note_id": note.id,
                "status": "saved",
                "category": note.category,
                "content": note.content,
            }, ensure_ascii=False)

        elif tool_name == "get_notes":
            from agent.notes_service import get_active_notes
            sub = get_sub(tool_input["phone"])
            notes = get_active_notes(sub)
            return json.dumps({
                "count": len(notes),
                "notes": [
                    {
                        "note_id": n.id,
                        "category": n.category,
                        "content": n.content,
                        "created_at": str(n.created_at),
                    }
                    for n in notes
                ],
            }, ensure_ascii=False)

        elif tool_name == "update_note":
            from agent.notes_service import update_note as svc_update_note
            sub = get_sub(tool_input["phone"])
            result = svc_update_note(
                subscriber=sub,
                note_id=tool_input["note_id"],
                content=tool_input.get("content"),
                is_active=tool_input.get("is_active"),
            )
            return json.dumps(result, ensure_ascii=False)

        else:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})

    except Subscriber.DoesNotExist:
        return json.dumps({
            "error": "Subscriber not found. They may need to register first."
        })
    except Exception as e:
        return json.dumps({"error": str(e)})

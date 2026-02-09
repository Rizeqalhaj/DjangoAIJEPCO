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
                "Get overall consumption summary for the subscriber over the last N days. "
                "Returns total kWh, average daily kWh, peak/off-peak split, "
                "highest/lowest day, cost estimate, and trend direction."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {"type": "string", "description": "Phone number"},
                    "days": {"type": "integer", "description": "Number of days to analyze (default 30)"},
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
                "Find unusual consumption spikes in the last N days. "
                "A spike is when power draw exceeds 2x the normal level for that hour. "
                "Returns timestamp, magnitude, duration, TOU period, and estimated extra cost."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {"type": "string", "description": "Phone number"},
                    "days": {"type": "integer", "description": "Number of days to analyze (default 7)"},
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
                "Create and save a new optimization plan for the subscriber. "
                "Call this ONLY after: (1) you've detected a pattern, "
                "(2) the user confirmed what's causing it, and "
                "(3) you've agreed on specific actions."
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
            "name": "check_plan_progress",
            "description": (
                "Compare current consumption data against the plan's baseline to "
                "check if the plan is working. Returns baseline vs actual, "
                "percentage change, and whether the target is being met."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {"type": "string", "description": "Phone number"},
                    "plan_id": {"type": "integer", "description": "Plan ID"},
                },
                "required": ["phone", "plan_id"],
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
            result = analyzer.detect_spikes(days=tool_input.get("days", 7))
            return json.dumps(result, ensure_ascii=False, default=str)

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
        return json.dumps({
            "error": "Subscriber not found. They may need to register first."
        })
    except Exception as e:
        return json.dumps({"error": str(e)})

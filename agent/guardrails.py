"""
Post-response guardrails that catch common LLM misbehavior programmatically.

These checks run AFTER the LLM produces a response but BEFORE it's sent to the user.
If a check fails, the response is patched or the LLM is re-prompted.
"""

import re
import logging

logger = logging.getLogger(__name__)


# --- Language mixing detection ---

# Arabic Unicode block: \u0600-\u06FF (Arabic), \u0750-\u077F (Arabic Supplement),
# \uFB50-\uFDFF (Arabic Presentation Forms-A), \uFE70-\uFEFF (Arabic Presentation Forms-B)
_ARABIC_RE = re.compile(r'[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]')

# Latin letters (ignoring common units like kWh, JOD, TOU, AM, PM, etc.)
_STRIP_ALLOWED_EN = re.compile(
    r'\b(?:k[Ww][Hh]|[Jj][Oo][Dd]|TOU|[AaPp][Mm]|JEPCO|EV|AC|kW|fils)\b'
)
_LATIN_RE = re.compile(r'[a-zA-Z]{3,}')  # 3+ consecutive Latin letters


def check_language_consistency(text: str, expected_language: str) -> dict | None:
    """
    Check if the response is in the expected language.

    Returns None if OK, or a dict with details if there's a violation.
    """
    if expected_language == "en":
        arabic_chars = len(_ARABIC_RE.findall(text))
        if arabic_chars > 3:
            return {
                "issue": "language_mixing",
                "detail": f"English response contains {arabic_chars} Arabic characters",
                "severity": "high",
            }
    elif expected_language == "ar":
        cleaned = _STRIP_ALLOWED_EN.sub('', text)
        latin_words = _LATIN_RE.findall(cleaned)
        if len(latin_words) > 5:
            return {
                "issue": "language_mixing",
                "detail": f"Arabic response contains {len(latin_words)} English words",
                "severity": "medium",
            }
    return None


# --- Tool usage validation ---

# Keywords that indicate the user asked a data question
_DATA_KEYWORDS_EN = re.compile(
    r'\b(consumption|usage|bill|kWh|how much|spent|cost|spike|pattern|forecast)\b',
    re.IGNORECASE,
)
_DATA_KEYWORDS_AR = re.compile(
    r'(استهلاك|فاتور|كهربا|كم|تكلف|ارتفاع|نمط|توقع|صرف)',
)


def check_tool_usage(
    user_message: str,
    tool_calls_made: int,
    language: str,
) -> dict | None:
    """
    Check if the agent called tools when it should have.

    Returns None if OK, or a dict with details if there's a violation.
    """
    pattern = _DATA_KEYWORDS_EN if language == "en" else _DATA_KEYWORDS_AR
    if pattern.search(user_message) and tool_calls_made == 0:
        return {
            "issue": "no_tool_calls",
            "detail": "User asked a data question but agent made 0 tool calls",
            "severity": "high",
        }
    return None


# --- Plan creation validation ---
# These detect when the agent CLAIMS the plan is saved/created without calling the tool.
# Merely describing/proposing a plan (Step 1 of the two-step flow) is fine without create_plan.

_PLAN_SAVED_EN = re.compile(
    r'\b(plan (?:is |has been )?(?:saved|created|set up|activated)|'
    r'saved (?:the|your) plan|plan is now active|I\'ve saved|I\'ve created)\b',
    re.IGNORECASE,
)
_PLAN_SAVED_AR = re.compile(
    r'(تم حفظ|تم إنشاء|حفظت الخطة|الخطة محفوظة|الخطة جاهزة|تم تفعيل)',
)


def check_plan_saved(
    response_text: str,
    tool_names_called: list[str],
    language: str,
) -> dict | None:
    """
    Check if the agent claimed a plan is saved but forgot to call create_plan.

    Only triggers when the agent says the plan IS saved/created (not when proposing one).
    The two-step flow allows describing a plan without calling create_plan (Step 1).

    Returns None if OK, or a dict with details if there's a violation.
    """
    pattern = _PLAN_SAVED_EN if language == "en" else _PLAN_SAVED_AR
    if pattern.search(response_text) and "create_plan" not in tool_names_called:
        return {
            "issue": "plan_not_saved",
            "detail": "Agent claimed plan is saved but did not call create_plan tool",
            "severity": "high",
        }
    return None


# --- Plan deletion validation ---
# Arabic morphology creates many word forms. Use root-based matching:
# - خط[ةطت] matches: خطة (plan), خطط (plans), خطت* (possessive base: خطتك, خطتي)
# - [أا]لغ matches both ألغ (with hamza) and الغ (without, common in informal Arabic)
_PLAN_NOUN_AR = r'(?:ال)?خط[ةطت]'

# Agent claims it deleted/cancelled (regardless of what user asked)
_AGENT_CLAIMED_DELETE_EN = re.compile(
    r'\b(cancel(?:led)?|delet(?:ed|ing)|remov(?:ed|ing)|'
    r'(?:I\'ve |I have )?(?:cancelled|deleted|removed))\b.*\b(plan)',
    re.IGNORECASE,
)
_AGENT_CLAIMED_DELETE_AR = re.compile(
    # Pattern 1: verb ... plan_noun (e.g., "تم إلغاء خطتك")
    rf'(تم إلغاء|تم حذف|لغيت|حذفت|ملغي|ملغية|إلغاء|[أا]لغ).*({_PLAN_NOUN_AR})|'
    # Pattern 2: plan_noun ... adjective (e.g., "كل الخطط ملغية")
    rf'({_PLAN_NOUN_AR}).*(ملغي|ملغية|محذوف|محذوفة)|'
    # Pattern 3: verb+pronoun suffix (e.g., "لغيتهم" = cancelled them)
    r'(لغيت|حذفت|[أا]لغيت)(هم|ها|هن)',
)

# User requests deletion
_USER_DELETE_EN = re.compile(
    r'\b(cancel|delete|remove)\b.*\b(plan)', re.IGNORECASE,
)
_USER_DELETE_AR = re.compile(
    rf'([أا]لغ|لغ[يى]|إلغاء|حذف|شيل).*({_PLAN_NOUN_AR}|بلان)',
)


def check_plan_deleted(
    response_text: str,
    user_message: str,
    tool_names_called: list[str],
    language: str,
) -> dict | None:
    """
    Check if the agent claims to have deleted a plan without calling delete_plan.

    Triggers in two scenarios:
    1. User asked to delete AND agent confirmed deletion — but no delete_plan called
    2. Agent claims deletion in its response — but no delete_plan called

    Returns None if OK, or a dict with details if there's a violation.
    """
    if "delete_plan" in tool_names_called:
        return None

    # If the agent checked plan status and found nothing, don't flag
    if "get_active_plan" in tool_names_called:
        return None

    # Scenario 1: agent CLAIMS deletion without calling the tool
    claim_pattern = _AGENT_CLAIMED_DELETE_EN if language == "en" else _AGENT_CLAIMED_DELETE_AR
    if claim_pattern.search(response_text):
        return {
            "issue": "plan_not_deleted",
            "detail": "Agent claimed plan is deleted/cancelled but did not call delete_plan tool",
            "severity": "high",
        }

    # Scenario 2: user asked to delete and agent responded affirmatively (no explicit claim)
    user_pattern = _USER_DELETE_EN if language == "en" else _USER_DELETE_AR
    if user_pattern.search(user_message) and "delete_plan" not in tool_names_called:
        # Only flag if agent didn't push back or ask for clarification
        pushback = re.search(r'(\?|which|sure|confirm|أي |متأكد|تأكيد)', response_text, re.IGNORECASE)
        if not pushback:
            return {
                "issue": "plan_not_deleted",
                "detail": "User asked to delete a plan but agent did not call delete_plan or ask for clarification",
                "severity": "high",
            }

    return None


def validate_response(
    response_text: str,
    user_message: str,
    language: str,
    tool_calls_made: int,
    tool_names_called: list[str],
) -> list[dict]:
    """
    Run all guardrail checks on the agent's response.

    Returns a list of violations (empty if all checks pass).
    """
    violations = []

    check = check_language_consistency(response_text, language)
    if check:
        violations.append(check)

    check = check_tool_usage(user_message, tool_calls_made, language)
    if check:
        violations.append(check)

    check = check_plan_saved(response_text, tool_names_called, language)
    if check:
        violations.append(check)

    check = check_plan_deleted(response_text, user_message, tool_names_called, language)
    if check:
        violations.append(check)

    if violations:
        logger.warning(
            "[Guardrails] %d violation(s) detected: %s",
            len(violations),
            [v["issue"] for v in violations],
        )

    return violations

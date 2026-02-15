"""Main agent class — the Smart Energy Detective."""

import json
import logging
import re

from core.llm_client import chat_with_tools, LLMError, MAIN_MODEL
from core.clock import now as clock_now
from agent.prompts import SYSTEM_PROMPT
from agent.tools import TOOLS, execute_tool
from agent.intent import classify_intent
from agent.conversation import ConversationManager
from agent.guardrails import validate_response

_ARABIC_CHARS_RE = re.compile(r'[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]')

logger = logging.getLogger(__name__)

MAX_USER_MESSAGE_LENGTH = 4000

FALLBACK_MESSAGES = {
    "ar": "عذراً، في مشكلة تقنية. حاول مرة ثانية بعد شوي. 🔧",
    "en": "Sorry, there's a technical issue. Please try again shortly. 🔧",
}


class EnergyDetective:
    """
    Main agent class. Handles a single user message end-to-end.
    """

    MAX_TOOL_ITERATIONS = 10

    def __init__(self):
        self.conv_manager = ConversationManager()

    def handle_message(self, phone: str, message: str) -> str:
        """
        Process an incoming message and return the agent's response.

        Steps:
        1. Load conversation history from cache
        2. Classify intent (fast model) — non-fatal on failure
        3. Append user message to history
        4. Send to LLM with tools
        5. Execute any tool calls in a loop
        6. Return final text response
        7. Save conversation history
        """
        # Truncate very long messages
        if len(message) > MAX_USER_MESSAGE_LENGTH:
            message = message[:MAX_USER_MESSAGE_LENGTH]

        logger.debug("=" * 60)
        logger.debug("[Agent] New message from %s: %r", phone, message[:80])

        # 1. Load conversation state
        state = self.conv_manager.get_state(phone)
        history = state.get("messages", [])
        language = state.get("language", "ar")
        logger.debug("[Agent] Loaded state: %d history msgs, cached_language=%s", len(history), language)

        # 2. Classify intent (non-fatal)
        try:
            intent_result = classify_intent(message)
            language = intent_result.get("language", language)
            logger.info(
                "[Agent] Intent: %s (%.0f%%), Language: %s",
                intent_result.get("intent"),
                intent_result.get("confidence", 0) * 100,
                language,
            )
        except Exception:
            logger.warning("[Agent] Intent classification failed, using defaults")
            intent_result = {
                "intent": "general",
                "confidence": 0.5,
                "language": language,
            }

        # Deterministic language override: if the message has zero Arabic
        # characters it is unambiguously English — don't trust the classifier.
        if not _ARABIC_CHARS_RE.search(message):
            if language != "en":
                logger.debug("[Agent] Language override: %s -> en (no Arabic chars in message)", language)
            language = "en"

        # 3. Append user message to history
        history.append({"role": "user", "content": message})

        # 4-5. Call LLM with tool loop
        logger.debug("[Agent] Starting LLM tool loop (language=%s)", language)
        tools_used = []
        try:
            final_text, tools_used = self._run_tool_loop(history, phone, language)
        except LLMError:
            logger.exception("[Agent] LLM failure for phone=%s", phone)
            final_text = FALLBACK_MESSAGES.get(language, FALLBACK_MESSAGES["ar"])
        except Exception:
            logger.exception("[Agent] Unexpected error for phone=%s", phone)
            final_text = FALLBACK_MESSAGES.get(language, FALLBACK_MESSAGES["ar"])

        # 6-7. Save conversation state (keep last 20 messages)
        history.append({"role": "assistant", "content": final_text})
        state["messages"] = history[-20:]
        state["language"] = language
        state["last_intent"] = intent_result.get("intent")
        self.conv_manager.save_state(phone, state)

        # Persist turn to database
        intent_str = intent_result.get("intent", "")
        try:
            self.conv_manager.save_turn(
                phone, message, final_text, intent_str,
                tools_used, language, state,
            )
        except Exception:
            logger.exception("[Agent] Failed to persist turn for phone=%s", phone)

        # Update subscriber language preference so notifications match
        self._update_subscriber_language(phone, language)

        logger.debug("[Agent] Response (%d chars): %s", len(final_text), final_text[:120])
        logger.debug("=" * 60)

        return final_text

    @staticmethod
    def _update_subscriber_language(phone: str, language: str):
        """Sync the subscriber's language field with the detected language."""
        try:
            from accounts.models import Subscriber
            Subscriber.objects.filter(phone_number=phone).update(language=language)
        except Exception:
            pass

    def _run_tool_loop(self, history: list, phone: str = "", language: str = "ar") -> tuple[str, list[str]]:
        """Execute the LLM call and tool-use loop. Returns (final_text, tool_names_called). May raise LLMError."""
        if language == "en":
            system = (
                "## LANGUAGE RULE (HIGHEST PRIORITY)\n"
                "The user is writing in English. Your ENTIRE response MUST be in English only. "
                "Do NOT include ANY Arabic text — not even a single word or phrase. "
                "This applies to everything: data, questions, follow-ups, greetings.\n\n"
            ) + SYSTEM_PROMPT
        else:
            system = SYSTEM_PROMPT + (
                "\n\n## LANGUAGE RULE (HIGHEST PRIORITY)\n"
                "The user is writing in Arabic. Your ENTIRE response MUST be in colloquial Jordanian Arabic only. "
                "Do NOT write English sentences or phrases. "
                "Exception: standard technical terms and units (kWh, JOD, JEPCO, TOU, AC, EV, fils, kW) may remain in English — "
                "do NOT translate these into Arabic."
            )
        # Inject current date/time so LLM can compute relative dates
        current_dt = clock_now()
        system += (
            f"\n\n## Current Date & Time\n"
            f"Today is {current_dt.strftime('%A, %Y-%m-%d')} "
            f"(time: {current_dt.strftime('%H:%M')}).\n"
            f"Use this to compute relative dates like 'yesterday', 'this week', 'last week', etc.\n"
            f"For 'this week', use Monday–Sunday of the current week.\n"
            f"For 'last week', use Monday–Sunday of the previous week."
        )
        if phone:
            system += (
                f"\n\n## Current Subscriber\n"
                f"Phone: {phone}\n"
                f"IMPORTANT: When calling any tool, use phone=\"{phone}\" as the phone parameter."
            )

            # Inject subscriber notes (long-term memory)
            try:
                from agent.notes_service import format_notes_for_prompt
                from accounts.models import Subscriber
                sub = Subscriber.objects.filter(phone_number=phone).first()
                if sub:
                    notes_block = format_notes_for_prompt(sub)
                    if notes_block:
                        system += f"\n\n{notes_block}"
            except Exception:
                logger.debug("[Agent] Failed to load subscriber notes, continuing without them")

        # Sanitize cached history: strip tool call/response messages from
        # previous turns (they lack the 'name' field Gemini requires).
        # Keep only user/assistant text messages from prior conversation.
        sanitized = []
        for msg_item in history:
            if msg_item.get("role") == "tool":
                continue
            if msg_item.get("role") == "assistant" and msg_item.get("tool_calls"):
                # Keep the assistant message but strip tool_calls
                sanitized.append({
                    "role": "assistant",
                    "content": msg_item.get("content") or "",
                })
                continue
            sanitized.append(msg_item)
        # Replace history in-place so the loop uses the clean version
        history.clear()
        history.extend(sanitized)

        logger.debug("[Agent] Calling LLM (model=%s, history=%d msgs)", MAIN_MODEL, len(history))
        response = chat_with_tools(
            messages=history,
            system=system,
            tools=TOOLS,
            model=MAIN_MODEL,
            max_tokens=2048,
        )

        iterations = 0
        msg = response.choices[0].message
        logger.debug("[Agent] LLM finish_reason=%s", response.choices[0].finish_reason)

        while (
            response.choices[0].finish_reason == "tool_calls"
            and msg.tool_calls
            and iterations < self.MAX_TOOL_ITERATIONS
        ):
            iterations += 1
            tool_names = [tc.function.name for tc in msg.tool_calls]
            logger.info("[Agent] Iteration %d — tool calls: %s", iterations, tool_names)

            # Append assistant message with tool calls
            history.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ],
            })

            # Execute each tool and append results
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except (json.JSONDecodeError, TypeError) as exc:
                    logger.warning(
                        "[Agent] Malformed tool args for %s: %s",
                        tc.function.name, exc,
                    )
                    history.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": tc.function.name,
                        "content": json.dumps({"error": f"Invalid arguments: {exc}"}),
                    })
                    continue

                try:
                    logger.debug("[Agent] Executing tool: %s(%s)", tc.function.name, tc.function.arguments[:100])
                    result = execute_tool(tc.function.name, args)
                    logger.debug("[Agent] Tool %s result: %s", tc.function.name, result[:200] if len(result) > 200 else result)
                except Exception as exc:
                    logger.warning(
                        "[Agent] Tool %s execution error: %s",
                        tc.function.name, exc,
                    )
                    result = json.dumps({"error": f"Tool execution failed: {exc}"})

                history.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": tc.function.name,
                    "content": result,
                })

            # Call LLM again with tool results
            logger.debug("[Agent] Re-calling LLM with tool results")
            response = chat_with_tools(
                messages=history,
                system=system,
                tools=TOOLS,
                model=MAIN_MODEL,
                max_tokens=2048,
            )
            msg = response.choices[0].message

        logger.info("[Agent] Done after %d tool iteration(s)", iterations)

        final_text = msg.content or ""
        logger.debug("[Agent] Raw LLM response: %s", final_text[:150])

        # --- Guardrail check ---
        # Collect all tool names called during this turn
        all_tool_names = []
        for h in history:
            if h.get("role") == "tool" and h.get("name"):
                all_tool_names.append(h["name"])

        # Get the original user message (last user msg before assistant replies)
        user_msg = ""
        for h in history:
            if h.get("role") == "user":
                user_msg = h.get("content", "")

        logger.debug("[Agent] Running guardrails (language=%s, tools_called=%s)", language, all_tool_names or "none")
        violations = validate_response(
            response_text=final_text,
            user_message=user_msg,
            language=language,
            tool_calls_made=iterations,
            tool_names_called=all_tool_names,
        )

        if not violations:
            logger.debug("[Agent] Guardrails: all checks passed")

        high_violations = [v for v in violations if v["severity"] == "high"]
        if high_violations:
            logger.warning(
                "[Guardrails] High-severity violations, re-prompting: %s",
                [v["issue"] for v in high_violations],
            )
            correction = self._build_correction_prompt(high_violations, language)
            history.append({"role": "assistant", "content": final_text})
            history.append({"role": "user", "content": correction})

            response = chat_with_tools(
                messages=history,
                system=system,
                tools=TOOLS,
                model=MAIN_MODEL,
                max_tokens=2048,
            )
            corrected = response.choices[0].message

            # If the correction triggers tool calls, run them
            if (
                response.choices[0].finish_reason == "tool_calls"
                and corrected.tool_calls
            ):
                corr_iterations = 0
                while (
                    response.choices[0].finish_reason == "tool_calls"
                    and corrected.tool_calls
                    and corr_iterations < 3
                ):
                    corr_iterations += 1
                    history.append({
                        "role": "assistant",
                        "content": corrected.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                },
                            }
                            for tc in corrected.tool_calls
                        ],
                    })
                    for tc in corrected.tool_calls:
                        try:
                            args = json.loads(tc.function.arguments)
                            result = execute_tool(tc.function.name, args)
                        except Exception as exc:
                            result = json.dumps({"error": str(exc)})
                        history.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "name": tc.function.name,
                            "content": result,
                        })
                    response = chat_with_tools(
                        messages=history,
                        system=system,
                        tools=TOOLS,
                        model=MAIN_MODEL,
                        max_tokens=2048,
                    )
                    corrected = response.choices[0].message

            final_text = corrected.content or final_text
            # Remove the correction exchange from history so it's not cached
            history.pop()  # remove correction user msg
            history.pop()  # remove original assistant msg

        return final_text, all_tool_names

    @staticmethod
    def _build_correction_prompt(violations: list[dict], language: str) -> str:
        """Build a correction prompt based on detected violations."""
        parts = []
        for v in violations:
            if v["issue"] == "language_mixing":
                if language == "en":
                    parts.append(
                        "Your previous response contained Arabic text. "
                        "Rewrite your ENTIRE response in English only — "
                        "no Arabic words or phrases at all."
                    )
                else:
                    parts.append(
                        "ردك السابق كان فيه كلمات إنجليزية. "
                        "أعد كتابة ردك كامل بالعربي فقط."
                    )
            elif v["issue"] == "no_tool_calls":
                parts.append(
                    "You answered a data question without calling any tools. "
                    "You MUST call the appropriate tool to get real data. "
                    "Do it now — call the tool and then answer with actual numbers."
                )
            elif v["issue"] == "plan_not_saved":
                parts.append(
                    "You claimed the plan is saved but did not call the create_plan tool. "
                    "Call create_plan NOW to actually save the plan to the database."
                )
            elif v["issue"] == "plan_not_deleted":
                parts.append(
                    "The user asked to delete/cancel their plan but you did not call the delete_plan tool. "
                    "Call delete_plan NOW to actually remove it from the database."
                )
        return " ".join(parts)

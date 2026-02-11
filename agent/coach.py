"""Main agent class — the Smart Energy Detective."""

import json
import logging

from core.llm_client import chat_with_tools, LLMError, MAIN_MODEL
from agent.prompts import SYSTEM_PROMPT
from agent.tools import TOOLS, execute_tool
from agent.intent import classify_intent
from agent.conversation import ConversationManager

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

        # 1. Load conversation state
        state = self.conv_manager.get_state(phone)
        history = state.get("messages", [])
        language = state.get("language", "ar")

        # 2. Classify intent (non-fatal)
        try:
            intent_result = classify_intent(message)
            language = intent_result.get("language", language)
            logger.info(
                "[Agent] Intent: %s, Language: %s",
                intent_result.get("intent"), language,
            )
        except Exception:
            logger.warning("[Agent] Intent classification failed, using defaults")
            intent_result = {
                "intent": "general",
                "confidence": 0.5,
                "language": language,
            }

        # 3. Append user message to history
        history.append({"role": "user", "content": message})

        # 4-5. Call LLM with tool loop
        try:
            final_text = self._run_tool_loop(history, phone)
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

        return final_text

    def _run_tool_loop(self, history: list, phone: str = "") -> str:
        """Execute the LLM call and tool-use loop. May raise LLMError."""
        system = SYSTEM_PROMPT
        if phone:
            system += (
                f"\n\n## Current Subscriber\n"
                f"Phone: {phone}\n"
                f"IMPORTANT: When calling any tool, use phone=\"{phone}\" as the phone parameter."
            )
        response = chat_with_tools(
            messages=history,
            system=system,
            tools=TOOLS,
            model=MAIN_MODEL,
            max_tokens=1024,
        )

        iterations = 0
        msg = response.choices[0].message

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
                        "content": json.dumps({"error": f"Invalid arguments: {exc}"}),
                    })
                    continue

                try:
                    result = execute_tool(tc.function.name, args)
                except Exception as exc:
                    logger.warning(
                        "[Agent] Tool %s execution error: %s",
                        tc.function.name, exc,
                    )
                    result = json.dumps({"error": f"Tool execution failed: {exc}"})

                history.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

            # Call LLM again with tool results
            response = chat_with_tools(
                messages=history,
                system=system,
                tools=TOOLS,
                model=MAIN_MODEL,
                max_tokens=1024,
            )
            msg = response.choices[0].message

        logger.info("[Agent] Done after %d tool iterations", iterations)
        return msg.content or ""

"""Main agent class — the Smart Energy Detective."""

import json
import logging
from core.llm_client import chat_with_tools, MAIN_MODEL
from agent.prompts import SYSTEM_PROMPT
from agent.tools import TOOLS, execute_tool
from agent.intent import classify_intent
from agent.conversation import ConversationManager

logger = logging.getLogger(__name__)


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
        2. Classify intent (fast model)
        3. Append user message to history
        4. Send to LLM with tools
        5. Execute any tool calls in a loop
        6. Return final text response
        7. Save conversation history
        """
        # 1. Load conversation state
        state = self.conv_manager.get_state(phone)
        history = state.get("messages", [])

        # 2. Classify intent
        logger.info("[Agent] Classifying intent for: %s", message[:50])
        intent_result = classify_intent(message)
        language = intent_result.get("language", "ar")
        logger.info("[Agent] Intent: %s, Language: %s", intent_result.get("intent"), language)

        # 3. Append user message to history
        history.append({"role": "user", "content": message})

        # 4. Call LLM with tools
        logger.info("[Agent] Calling LLM with %d messages", len(history))
        response = chat_with_tools(
            messages=history,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            model=MAIN_MODEL,
            max_tokens=1024,
        )

        # 5. Tool use loop (OpenAI-compatible format)
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
                args = json.loads(tc.function.arguments)
                result = execute_tool(tc.function.name, args)
                history.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

            # Call LLM again with tool results
            response = chat_with_tools(
                messages=history,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                model=MAIN_MODEL,
                max_tokens=1024,
            )
            msg = response.choices[0].message

        # 6. Extract final text
        logger.info("[Agent] Done after %d tool iterations", iterations)
        final_text = msg.content or ""
        history.append({"role": "assistant", "content": final_text})

        # 7. Save conversation state (keep last 20 messages)
        state["messages"] = history[-20:]
        state["language"] = language
        state["last_intent"] = intent_result.get("intent")
        self.conv_manager.save_state(phone, state)

        return final_text

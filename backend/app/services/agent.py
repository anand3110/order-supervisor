import json
import time

from google import genai
from google.genai import types
from google.genai.errors import ClientError, ServerError

from app.config import settings
from app.schemas.agent import AgentDecision


ALLOWED_ACTIONS = {
    "message_fulfillment_team",
    "message_payments_team",
    "message_logistics_team",
    "message_customer",
    "create_internal_note",
}


client = genai.Client(api_key=settings.gemini_api_key)


def ask_agent(
    base_instruction: str,
    run_instructions: list[str],
    state: dict,
    events: list[dict],
    model: str = "gemini-3.7-flash",
) -> AgentDecision:

    prompt = {
        "base_instruction": base_instruction,
        "run_instructions": run_instructions,
        "current_state": state,
        "recent_events": events,
        "available_actions": list(ALLOWED_ACTIONS),
    }

    system_instruction = """
You are an AI supervisor responsible for monitoring a single customer order.

Your job is to analyze:
- the supervisor's base instruction
- any run-specific instructions
- the current order state
- recent order events

Then decide whether any operational actions are required.

Available actions are:
- message_fulfillment_team
- message_payments_team
- message_logistics_team
- message_customer
- create_internal_note

Rules:
1. Only use actions from the available actions list.
2. Do not invent new action names.
3. If no action is required, return an empty actions list.
4. Give a short explanation of your reasoning.
5. Choose a reasonable sleep duration between 1 and 60 minutes.
6. Never decide that the order supervisor run is completed.
7. Run completion is controlled by the backend/system.
8. Do not claim that an action was actually executed. Only recommend the action.
"""

    request_content = (
        system_instruction
        + "\n\nOrder supervision input:\n"
        + json.dumps(prompt, indent=2)
    )

    max_attempts = 3

    for attempt in range(max_attempts):
        try:
            response = client.models.generate_content(
                model=model,
                contents=request_content,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=AgentDecision,
                ),
            )

            return AgentDecision.model_validate_json(response.text)

        except ClientError as error:
            error_text = str(error)

            if "429" in error_text or "RESOURCE_EXHAUSTED" in error_text:
                print(
                    "[Agent] Gemini quota is exhausted. "
                    "No automated action was taken. "
                    "The supervisor will retry later."
                )

                return AgentDecision(
                    reasoning=(
                        "Gemini quota is temporarily unavailable. "
                        "No automated action was taken. "
                        "The supervisor will retry on a later wake-up."
                    ),
                    actions=[],
                    sleep_minutes=5,
                )

            raise

        except ServerError as error:
            error_text = str(error)

            is_temporary_error = (
                "503" in error_text
                or "UNAVAILABLE" in error_text
            )

            if not is_temporary_error:
                raise

            if attempt == max_attempts - 1:
                print(
                    "[Agent] Gemini is still unavailable "
                    "after retries. Deferring decision."
                )

                return AgentDecision(
                    reasoning=(
                        "Gemini was temporarily unavailable. "
                        "No automated action was taken. "
                        "The supervisor will retry on a later wake-up."
                    ),
                    actions=[],
                    sleep_minutes=1,
                )

            wait_seconds = 2 ** attempt

            print(
                f"[Agent] Gemini temporarily unavailable. "
                f"Retrying in {wait_seconds}s..."
            )

            time.sleep(wait_seconds)

    return AgentDecision(
        reasoning="No decision was produced.",
        actions=[],
        sleep_minutes=1,
    )
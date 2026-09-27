import time

from google import genai
from google.genai import types

from app.config import settings
from app.schemas.agent import AgentDecision


ALLOWED_ACTIONS = {
    "message_fulfillment_team",
    "message_payments_team",
    "message_logistics_team",
    "message_customer",
    "create_internal_note",
}


client = genai.Client(
    api_key=settings.gemini_api_key
)


MODEL_NAME = "gemini-3.8-flash"


def ask_agent(
    base_instruction: str,
    run_instructions: list[str],
    state: dict,
    events: list[dict],
    model: str = MODEL_NAME,
) -> AgentDecision:

    system_instruction = """
You are an AI supervisor responsible for monitoring a single customer order.

Analyze:
- the supervisor's base instruction
- run-specific instructions
- current order state
- recent order events

Then decide whether operational actions are required.

Available actions:
- message_fulfillment_team
- message_payments_team
- message_logistics_team
- message_customer
- create_internal_note

Rules:
1. Only use the available action names.
2. Do not invent action names.
3. If no action is required, return an empty actions array.
4. Give a short explanation of your reasoning.
5. Choose a sleep duration between 1 and 60 minutes.
6. Never decide that the supervisor run is completed.
7. Completion is controlled by the backend.
8. Do not claim that an action was actually executed.
9. Only recommend actions.
"""


    prompt = f"""
{system_instruction}

Supervisor base instruction:
{base_instruction}

Run-specific instructions:
{run_instructions}

Current order state:
{state}

Recent order events:
{events}

Decide what the supervisor should do next.
"""


    max_attempts = 3

    for attempt in range(max_attempts):

        try:

            print(
                f"[Agent] Calling Gemini model: {model}"
            )

            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=AgentDecision,
                ),
            )

            if not response.text:

                raise ValueError(
                    "Gemini returned an empty response."
                )

            print("[Agent] Raw Gemini response:")
            print(response.text)

            # Gemini structured output should already
            # be valid JSON matching AgentDecision.
            decision = AgentDecision.model_validate_json(
                response.text
            )

            # ---------------------------------------------------------
            # Backend validation
            # ---------------------------------------------------------

            validated_actions = []

            for action in decision.actions:

                if action.action in ALLOWED_ACTIONS:

                    validated_actions.append(action)

                else:

                    print(
                        "[Agent] Ignoring invalid action from model: "
                        f"{action.action}"
                    )

            decision.actions = validated_actions

            # ---------------------------------------------------------
            # Log final decision
            # ---------------------------------------------------------

            print("[Agent] Gemini decision:")

            print(
                f"[Agent] Reasoning: "
                f"{decision.reasoning}"
            )

            print(
                "[Agent] Actions: "
                f"{[a.action for a in decision.actions]}"
            )

            print(
                f"[Agent] Sleep: "
                f"{decision.sleep_minutes} minutes"
            )

            return decision


        except Exception as error:

            print(
                f"[Agent] Gemini error "
                f"on attempt {attempt + 1}:"
            )

            print(
                f"[Agent] Error type: "
                f"{type(error).__name__}"
            )

            print(
                f"[Agent] Error: {error}"
            )

            # Retry twice if the first attempts fail.
            if attempt < max_attempts - 1:

                wait_seconds = 2 ** attempt

                print(
                    f"[Agent] Retrying in "
                    f"{wait_seconds}s..."
                )

                time.sleep(wait_seconds)

            else:

                return AgentDecision(
                    reasoning=(
                        "The Gemini model was temporarily "
                        "unavailable. No automated action "
                        "was taken."
                    ),
                    actions=[],
                    sleep_minutes=1,
                )


    return AgentDecision(
        reasoning="No decision was produced.",
        actions=[],
        sleep_minutes=1,
    )
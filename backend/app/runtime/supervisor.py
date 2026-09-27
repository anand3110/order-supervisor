from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.db.models import (
    Activity,
    Event,
    Order,
    Run,
    RunInstruction,
    RunStatus,
    Supervisor,
)
from app.services.agent import ask_agent
from app.services.actions import (
    create_internal_note,
    message_customer,
    message_fulfillment_team,
    message_logistics_team,
    message_payments_team,
)


# Maximum amount of time a supervisor run is allowed to live.
MAX_RUN_AGE = timedelta(hours=24)


ACTION_HANDLERS = {
    "message_fulfillment_team": message_fulfillment_team,
    "message_payments_team": message_payments_team,
    "message_logistics_team": message_logistics_team,
    "message_customer": message_customer,
    "create_internal_note": create_internal_note,
}


def has_exceeded_max_age(run: Run) -> bool:
    """
    Check whether the supervisor run has exceeded its maximum lifetime.
    """

    if run.started_at is None:
        return False

    now = datetime.now(timezone.utc)

    return now - run.started_at >= MAX_RUN_AGE


def terminate_due_to_max_age(run: Run, db: Session):
    """
    System-owned termination when a run exceeds its maximum lifetime.
    """

    now = datetime.now(timezone.utc)

    run.status = RunStatus.TERMINATED
    run.ended_at = now
    run.next_wake_at = None

    run.final_summary = (
        "The supervisor run was automatically terminated because "
        "it exceeded the maximum allowed runtime of 24 hours."
    )

    run.learnings = (
        "The run remained active longer than the configured "
        "maximum supervisor lifetime."
    )

    run.recommendations = (
        "Review the order manually if supervision is still required."
    )

    activity = Activity(
        run_id=run.id,
        activity_type="system",
        action=None,
        content=(
            "Supervisor run automatically terminated because "
            "the maximum run age of 24 hours was exceeded."
        ),
        metadata_={
            "reason": "max_run_age_exceeded",
            "max_run_age_hours": 24,
        },
    )

    db.add(activity)


def update_state_from_event(run: Run, event: Event, db: Session):
    if event.event_type == "payment_confirmed":
        run.state["payment_status"] = "confirmed"

    elif event.event_type == "payment_failed":
        run.state["payment_status"] = "failed"

    elif event.event_type == "shipment_created":
        run.state["shipment_status"] = "created"

    elif event.event_type == "shipment_delayed":
        run.state["shipment_status"] = "delayed"

    elif event.event_type == "delivered":
        run.state["order_status"] = "delivered"

        order = db.get(Order, run.order_id)

        if order is not None:
            order.status = "delivered"

    elif event.event_type == "refund_requested":
        run.state["refund_status"] = "requested"

    elif event.event_type == "customer_message_received":
        run.state["customer_message"] = event.payload

    elif event.event_type == "order_created":
        run.state["order_status"] = "created"

    elif event.event_type == "no_update_for_n_hours":
        run.state["no_update"] = True
        run.state["no_update_payload"] = event.payload

    else:
        run.state["last_unknown_event"] = event.event_type

    run.state["last_event"] = event.event_type
    run.state["last_event_id"] = str(event.id)

    flag_modified(run, "state")


def get_recent_events(run: Run, db: Session):
    events = (
        db.query(Event)
        .filter(Event.run_id == run.id)
        .order_by(Event.created_at.desc())
        .limit(10)
        .all()
    )

    events.reverse()

    return [
        {
            "event_type": event.event_type,
            "payload": event.payload,
            "created_at": (
                event.created_at.isoformat()
                if event.created_at
                else None
            ),
        }
        for event in events
    ]


def get_run_instructions(run: Run, db: Session):
    instructions = (
        db.query(RunInstruction)
        .filter(RunInstruction.run_id == run.id)
        .order_by(RunInstruction.created_at.asc())
        .all()
    )

    return [
        instruction.instruction
        for instruction in instructions
    ]


def execute_agent_actions(run: Run, decision, db: Session):
    for agent_action in decision.actions:

        handler = ACTION_HANDLERS.get(agent_action.action)

        if handler is None:
            create_internal_note(
                run.id,
                f"Blocked invalid agent action: {agent_action.action}",
                db,
            )
            continue

        handler(
            run.id,
            agent_action.content,
            db,
        )


def record_agent_reasoning(
    run: Run,
    reasoning: str,
    db: Session,
):
    activity = Activity(
        run_id=run.id,
        activity_type="agent_reasoning",
        action=None,
        content=reasoning,
        metadata_={},
    )

    db.add(activity)


def process_events(run: Run, db: Session):
    events = (
        db.query(Event)
        .filter(
            Event.run_id == run.id,
            Event.processed_at.is_(None),
        )
        .order_by(Event.created_at.asc())
        .all()
    )

    for event in events:

        update_state_from_event(
            run,
            event,
            db,
        )

        event.processed_at = datetime.now(timezone.utc)

        # Delivery is a system-owned terminal event.
        if event.event_type == "delivered":

            run.status = RunStatus.COMPLETED
            run.ended_at = datetime.now(timezone.utc)

            run.final_summary = (
                "Order was successfully delivered. "
                "The supervisor monitored the order lifecycle "
                "and completed the run."
            )

            run.learnings = (
                "The order progressed through its lifecycle "
                "until delivery."
            )

            run.recommendations = (
                "No further action is required because the order "
                "reached the terminal delivered state."
            )

            break


def execute_safety_fallback(run: Run, db: Session):
    event_type = run.state.get("last_event")
    event_id = run.state.get("last_event_id")

    if not event_type or not event_id:
        return

    if run.state.get("last_fallback_event_id") == event_id:
        return

    if event_type == "shipment_delayed":

        message_logistics_team(
            run.id,
            (
                "Shipment delay detected. Please investigate the delay "
                "and provide the latest expected delivery status."
            ),
            db,
        )

        message_customer(
            run.id,
            (
                "We are sorry, but your shipment has been delayed. "
                "Our logistics team is investigating the issue and "
                "will provide an updated delivery status."
            ),
            db,
        )

        create_internal_note(
            run.id,
            (
                "Safety fallback triggered for shipment_delayed "
                "because the AI model was temporarily unavailable."
            ),
            db,
        )

    elif event_type == "payment_failed":

        message_payments_team(
            run.id,
            (
                "Payment failure detected. Please investigate the "
                "payment issue and confirm the current payment status."
            ),
            db,
        )

        create_internal_note(
            run.id,
            (
                "Safety fallback triggered for payment_failed "
                "because the AI model was temporarily unavailable."
            ),
            db,
        )

    elif event_type == "refund_requested":

        message_payments_team(
            run.id,
            (
                "A refund has been requested. Please review the request "
                "and verify the appropriate refund workflow."
            ),
            db,
        )

        create_internal_note(
            run.id,
            (
                "Safety fallback triggered for refund_requested "
                "because the AI model was temporarily unavailable."
            ),
            db,
        )

    elif event_type == "customer_message_received":

        create_internal_note(
            run.id,
            (
                "Customer message received while AI inference was "
                "temporarily unavailable. Manual review may be required."
            ),
            db,
        )

    else:
        return

    run.state["last_fallback_event_id"] = event_id

    flag_modified(run, "state")


def run_supervisor(run: Run, db: Session):

    if run.status != RunStatus.RUNNING:
        return

    # ------------------------------------------------
    # 1. System-owned maximum runtime check
    # ------------------------------------------------

    if has_exceeded_max_age(run):

        terminate_due_to_max_age(
            run,
            db,
        )

        db.commit()
        db.refresh(run)

        return

    # ------------------------------------------------
    # 2. Process incoming events
    # ------------------------------------------------

    process_events(
        run,
        db,
    )

    # A terminal event such as "delivered"
    # can complete the run before AI inference.
    if run.status == RunStatus.COMPLETED:

        db.commit()
        db.refresh(run)

        return

    # ------------------------------------------------
    # 3. Load supervisor configuration
    # ------------------------------------------------

    supervisor = db.get(
        Supervisor,
        run.supervisor_id,
    )

    if supervisor is None:
        raise RuntimeError(
            "Supervisor configuration not found."
        )

    # ------------------------------------------------
    # 4. Gather context for the agent
    # ------------------------------------------------

    recent_events = get_recent_events(
        run,
        db,
    )

    run_instructions = get_run_instructions(
        run,
        db,
    )

    # ------------------------------------------------
    # 5. Ask the AI for a decision
    # ------------------------------------------------

    decision = ask_agent(
        base_instruction=supervisor.base_instruction,
        run_instructions=run_instructions,
        state=run.state,
        events=recent_events,
        model=supervisor.model,
    )

    # ------------------------------------------------
    # 6. Record agent reasoning
    # ------------------------------------------------

    record_agent_reasoning(
        run,
        decision.reasoning,
        db,
    )

    # ------------------------------------------------
    # 7. Execute actions
    # ------------------------------------------------

    if "Gemini quota is temporarily unavailable" in decision.reasoning:

        execute_safety_fallback(
            run,
            db,
        )

    else:

        execute_agent_actions(
            run,
            decision,
            db,
        )

    # ------------------------------------------------
    # 8. Persist supervisor state
    # ------------------------------------------------

    run.state["last_supervisor_check"] = (
        datetime.now(timezone.utc).isoformat()
    )

    run.state["last_agent_sleep_minutes"] = (
        decision.sleep_minutes
    )

    flag_modified(
        run,
        "state",
    )

    # ------------------------------------------------
    # 9. Put the run to sleep
    # ------------------------------------------------

    run.status = RunStatus.SLEEPING

    run.next_wake_at = (
        datetime.now(timezone.utc)
        + timedelta(
            minutes=decision.sleep_minutes
        )
    )

    db.commit()
    db.refresh(run)
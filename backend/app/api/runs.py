from uuid import UUID
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import (
    Activity,
    Event,
    Order,
    Run,
    RunInstruction,
    RunStatus,
    Supervisor,
)
from app.schemas.run import (
    EventCreate,
    RunCreate,
    RunInstructionCreate,
    RunResponse,
)
from app.runtime.supervisor import run_supervisor


router = APIRouter(prefix="/api/runs", tags=["Runs"])


@router.post("/", response_model=RunResponse, status_code=201)
def create_run(
    data: RunCreate,
    db: Session = Depends(get_db),
):
    order = db.get(Order, data.order_id)

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found",
        )

    supervisor = db.get(
        Supervisor,
        data.supervisor_id,
    )

    if supervisor is None:
        raise HTTPException(
            status_code=404,
            detail="Supervisor not found",
        )

    # One supervisor run per order.
    existing_run = (
        db.query(Run)
        .filter(Run.order_id == data.order_id)
        .first()
    )

    if existing_run is not None:
        raise HTTPException(
            status_code=409,
            detail="A supervisor run already exists for this order",
        )

    run = Run(
        order_id=data.order_id,
        supervisor_id=data.supervisor_id,
        status=RunStatus.CREATED,
        state={
            "order_status": order.status,
            "customer_name": order.customer_name,
        },
    )

    db.add(run)
    db.commit()
    db.refresh(run)

    return run


@router.get("/", response_model=list[RunResponse])
def get_runs(
    db: Session = Depends(get_db),
):
    runs = (
        db.query(Run)
        .order_by(Run.created_at.desc())
        .all()
    )

    return runs


@router.get("/{run_id}", response_model=RunResponse)
def get_run(
    run_id: UUID,
    db: Session = Depends(get_db),
):
    run = db.get(Run, run_id)

    if run is None:
        raise HTTPException(
            status_code=404,
            detail="Run not found",
        )

    return run


@router.post(
    "/{run_id}/start",
    response_model=RunResponse,
)
def start_run(
    run_id: UUID,
    db: Session = Depends(get_db),
):
    run = db.get(Run, run_id)

    if run is None:
        raise HTTPException(
            status_code=404,
            detail="Run not found",
        )

    if run.status != RunStatus.CREATED:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Run cannot be started from status: "
                f"{run.status.value}"
            ),
        )

    run.status = RunStatus.RUNNING
    run.started_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(run)

    # Execute the first supervisor cycle immediately.
    run_supervisor(run, db)

    return run


@router.post("/{run_id}/events")
def create_event(
    run_id: UUID,
    data: EventCreate,
    db: Session = Depends(get_db),
):
    run = db.get(Run, run_id)

    if run is None:
        raise HTTPException(
            status_code=404,
            detail="Run not found",
        )

    # Do not accept new events for terminal runs.
    if run.status in {
        RunStatus.COMPLETED,
        RunStatus.TERMINATED,
        RunStatus.INTERRUPTED,
    }:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Cannot add events to a "
                f"{run.status.value} run"
            ),
        )

    event = Event(
        run_id=run.id,
        event_type=data.event_type,
        payload=data.payload,
    )

    db.add(event)
    db.flush()

    # An incoming event wakes a sleeping run.
    if run.status == RunStatus.SLEEPING:
        run.status = RunStatus.RUNNING
        run.next_wake_at = None

    db.commit()
    db.refresh(run)
    db.refresh(event)

    # Process the event immediately if the run is active.
    if run.status == RunStatus.RUNNING:
        run_supervisor(run, db)

    return {
        "event_id": event.id,
        "run_id": event.run_id,
        "event_type": event.event_type,
        "payload": event.payload,
        "message": "Event received and processed",
    }


@router.get("/{run_id}/activities")
def get_run_activities(
    run_id: UUID,
    db: Session = Depends(get_db),
):
    run = db.get(Run, run_id)

    if run is None:
        raise HTTPException(
            status_code=404,
            detail="Run not found",
        )

    activities = (
        db.query(Activity)
        .filter(Activity.run_id == run_id)
        .order_by(Activity.created_at.asc())
        .all()
    )

    return [
        {
            "id": activity.id,
            "activity_type": activity.activity_type,
            "action": activity.action,
            "content": activity.content,
            "created_at": activity.created_at,
        }
        for activity in activities
    ]


@router.get("/{run_id}/events")
def get_run_events(
    run_id: UUID,
    db: Session = Depends(get_db),
):
    run = db.get(Run, run_id)

    if run is None:
        raise HTTPException(
            status_code=404,
            detail="Run not found",
        )

    events = (
        db.query(Event)
        .filter(Event.run_id == run_id)
        .order_by(Event.created_at.asc())
        .all()
    )

    return [
        {
            "id": event.id,
            "event_type": event.event_type,
            "payload": event.payload,
            "created_at": event.created_at,
            "processed_at": event.processed_at,
        }
        for event in events
    ]


@router.post(
    "/{run_id}/pause",
    response_model=RunResponse,
)
def pause_run(
    run_id: UUID,
    db: Session = Depends(get_db),
):
    run = db.get(Run, run_id)

    if run is None:
        raise HTTPException(
            status_code=404,
            detail="Run not found",
        )

    if run.status not in {
        RunStatus.RUNNING,
        RunStatus.SLEEPING,
    }:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Run cannot be paused from status: "
                f"{run.status.value}"
            ),
        )

    run.status = RunStatus.PAUSED
    run.next_wake_at = None

    db.commit()
    db.refresh(run)

    return run


@router.post(
    "/{run_id}/resume",
    response_model=RunResponse,
)
def resume_run(
    run_id: UUID,
    db: Session = Depends(get_db),
):
    run = db.get(Run, run_id)

    if run is None:
        raise HTTPException(
            status_code=404,
            detail="Run not found",
        )

    if run.status != RunStatus.PAUSED:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Run cannot be resumed from status: "
                f"{run.status.value}"
            ),
        )

    run.status = RunStatus.RUNNING
    run.next_wake_at = None

    db.commit()
    db.refresh(run)

    run_supervisor(run, db)

    return run


@router.post(
    "/{run_id}/interrupt",
    response_model=RunResponse,
)
def interrupt_run(
    run_id: UUID,
    db: Session = Depends(get_db),
):
    run = db.get(Run, run_id)

    if run is None:
        raise HTTPException(
            status_code=404,
            detail="Run not found",
        )

    if run.status not in {
        RunStatus.RUNNING,
        RunStatus.SLEEPING,
        RunStatus.PAUSED,
    }:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Run cannot be interrupted from status: "
                f"{run.status.value}"
            ),
        )

    run.status = RunStatus.INTERRUPTED
    run.next_wake_at = None

    db.commit()
    db.refresh(run)

    return run


@router.post(
    "/{run_id}/terminate",
    response_model=RunResponse,
)
def terminate_run(
    run_id: UUID,
    db: Session = Depends(get_db),
):
    run = db.get(Run, run_id)

    if run is None:
        raise HTTPException(
            status_code=404,
            detail="Run not found",
        )

    if run.status in {
        RunStatus.COMPLETED,
        RunStatus.TERMINATED,
    }:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Run cannot be terminated from status: "
                f"{run.status.value}"
            ),
        )

    run.status = RunStatus.TERMINATED
    run.next_wake_at = None
    run.ended_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(run)

    return run


@router.post("/{run_id}/instructions")
def add_run_instruction(
    run_id: UUID,
    data: RunInstructionCreate,
    db: Session = Depends(get_db),
):
    run = db.get(Run, run_id)

    if run is None:
        raise HTTPException(
            status_code=404,
            detail="Run not found",
        )

    if run.status in {
        RunStatus.COMPLETED,
        RunStatus.TERMINATED,
        RunStatus.INTERRUPTED,
    }:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Cannot add instructions to a "
                f"{run.status.value} run"
            ),
        )

    instruction = RunInstruction(
        run_id=run.id,
        instruction=data.instruction,
    )

    db.add(instruction)
    db.commit()
    db.refresh(instruction)

    return {
        "id": instruction.id,
        "run_id": instruction.run_id,
        "instruction": instruction.instruction,
        "created_at": instruction.created_at,
    }


@router.get("/{run_id}/instructions")
def get_run_instructions(
    run_id: UUID,
    db: Session = Depends(get_db),
):
    run = db.get(Run, run_id)

    if run is None:
        raise HTTPException(
            status_code=404,
            detail="Run not found",
        )

    instructions = (
        db.query(RunInstruction)
        .filter(RunInstruction.run_id == run_id)
        .order_by(RunInstruction.created_at.asc())
        .all()
    )

    return [
        {
            "id": instruction.id,
            "instruction": instruction.instruction,
            "created_at": instruction.created_at,
        }
        for instruction in instructions
    ]
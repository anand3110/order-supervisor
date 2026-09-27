from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.db.models import RunStatus


class RunCreate(BaseModel):
    order_id: UUID
    supervisor_id: UUID


class RunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_id: UUID
    supervisor_id: UUID
    status: RunStatus
    state: dict
    next_wake_at: datetime | None
    started_at: datetime | None
    ended_at: datetime | None
    final_summary: str | None
    learnings: str | None
    recommendations: str | None


class EventCreate(BaseModel):
    event_type: str
    payload: dict = {}


class RunInstructionCreate(BaseModel):
    instruction: str
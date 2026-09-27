import enum
import uuid

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class RunStatus(str, enum.Enum):
    CREATED = "created"
    RUNNING = "running"
    SLEEPING = "sleeping"
    PAUSED = "paused"
    INTERRUPTED = "interrupted"
    TERMINATED = "terminated"
    COMPLETED = "completed"


class Supervisor(Base):
    __tablename__ = "supervisors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    name: Mapped[str] = mapped_column(String(100))
    base_instruction: Mapped[str] = mapped_column(Text)

    model: Mapped[str] = mapped_column(
        String(100),
        default="gemini-3.7-flash",
    )

    wake_policy: Mapped[str] = mapped_column(
        String(100),
        default="important_events",
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    customer_name: Mapped[str] = mapped_column(String(200))
    amount: Mapped[float] = mapped_column(Numeric(10, 2))

    status: Mapped[str] = mapped_column(
        String(50),
        default="created",
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id"),
    )

    supervisor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("supervisors.id"),
    )

    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus),
        default=RunStatus.CREATED,
    )

    state: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
    )

    next_wake_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    started_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    ended_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    final_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    learnings: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    recommendations: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runs.id"),
    )

    event_type: Mapped[str] = mapped_column(
        String(100),
    )

    payload: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    processed_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runs.id"),
    )

    activity_type: Mapped[str] = mapped_column(
        String(50),
    )

    action: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    content: Mapped[str] = mapped_column(
        Text,
    )

    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class RunInstruction(Base):
    __tablename__ = "run_instructions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runs.id"),
    )

    instruction: Mapped[str] = mapped_column(
        Text,
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
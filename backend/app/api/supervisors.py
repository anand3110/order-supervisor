from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Supervisor
from app.schemas.supervisor import (
    SupervisorCreate,
    SupervisorResponse,
)


router = APIRouter(
    prefix="/api/supervisors",
    tags=["Supervisors"],
)


@router.post(
    "/",
    response_model=SupervisorResponse,
)
def create_supervisor(
    data: SupervisorCreate,
    db: Session = Depends(get_db),
):
    supervisor = Supervisor(
        name=data.name,
        base_instruction=data.base_instruction,
        model=data.model,
        wake_policy=data.wake_policy,
    )

    db.add(supervisor)
    db.commit()
    db.refresh(supervisor)

    return supervisor


@router.get(
    "/{supervisor_id}",
    response_model=SupervisorResponse,
)
def get_supervisor(
    supervisor_id: UUID,
    db: Session = Depends(get_db),
):
    supervisor = db.get(
        Supervisor,
        supervisor_id,
    )

    if supervisor is None:
        raise HTTPException(
            status_code=404,
            detail="Supervisor not found",
        )

    return supervisor
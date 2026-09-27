from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import Activity


def _create_activity(
    run_id: UUID,
    activity_type: str,
    action: str,
    content: str,
    db: Session,
):
    """
    Create an activity record for a supervisor action.
    """

    activity = Activity(
        run_id=run_id,
        activity_type=activity_type,
        action=action,
        content=content,
        metadata_={},
    )

    db.add(activity)
    db.commit()
    db.refresh(activity)

    return activity


def message_fulfillment_team(
    run_id: UUID,
    content: str,
    db: Session,
):
    return _create_activity(
        run_id=run_id,
        activity_type="action",
        action="message_fulfillment_team",
        content=content,
        db=db,
    )


def message_payments_team(
    run_id: UUID,
    content: str,
    db: Session,
):
    return _create_activity(
        run_id=run_id,
        activity_type="action",
        action="message_payments_team",
        content=content,
        db=db,
    )


def message_logistics_team(
    run_id: UUID,
    content: str,
    db: Session,
):
    return _create_activity(
        run_id=run_id,
        activity_type="action",
        action="message_logistics_team",
        content=content,
        db=db,
    )


def message_customer(
    run_id: UUID,
    content: str,
    db: Session,
):
    return _create_activity(
        run_id=run_id,
        activity_type="action",
        action="message_customer",
        content=content,
        db=db,
    )


def create_internal_note(
    run_id: UUID,
    content: str,
    db: Session,
):
    return _create_activity(
        run_id=run_id,
        activity_type="internal_note",
        action="create_internal_note",
        content=content,
        db=db,
    )
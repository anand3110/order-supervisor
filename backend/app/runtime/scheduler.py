import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.database import SessionLocal
from app.db.models import Run, RunStatus
from app.runtime.supervisor import run_supervisor


async def scheduler_loop():
    while True:
        db = SessionLocal()

        try:
            now = datetime.now(timezone.utc)

            runs = db.scalars(
                select(Run)
                .where(
                    Run.status == RunStatus.SLEEPING,
                    Run.next_wake_at <= now,
                )
                .with_for_update(skip_locked=True)
            ).all()

            for run in runs:
                print(f"[Scheduler] Waking run {run.id}")

                run.status = RunStatus.RUNNING
                run.next_wake_at = None

                db.commit()

                run_supervisor(run, db)

        except Exception as e:
            db.rollback()
            print(f"[Scheduler] Error: {e}")

        finally:
            db.close()

        await asyncio.sleep(10)
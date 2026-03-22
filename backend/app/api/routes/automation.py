"""
Automation / scheduler routes — trigger background jobs.
Can be called by APScheduler or externally via API key.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin_user, get_db
from app.models.models import AutomationRun

router = APIRouter(prefix="/automation", tags=["automation"])


class AutomationRunRequest(BaseModel):
    run_type: str        # daily_word, scheduled_lesson, weekly_report, etc.
    payload: dict = {}
    user_id: str | None = None


@router.post("/run")
async def trigger_automation(
    body: AutomationRunRequest,
    _=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger a background automation job."""
    run = AutomationRun(
        user_id=None if not body.user_id else body.user_id,
        run_type=body.run_type,
        status="pending",
        payload=body.payload,
        started_at=datetime.now(UTC),
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    # In production, push to Celery/ARQ queue here
    # For now, return the job ID for tracking
    return {
        "success": True,
        "run_id": str(run.id),
        "run_type": run.run_type,
        "status": run.status,
    }


@router.get("/runs")
async def list_automation_runs(
    limit: int = 20,
    _=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    result = await db.execute(
        select(AutomationRun).order_by(AutomationRun.created_at.desc()).limit(limit)
    )
    runs = result.scalars().all()
    return {
        "runs": [
            {
                "id": str(r.id),
                "run_type": r.run_type,
                "status": r.status,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "error": r.error,
            }
            for r in runs
        ]
    }

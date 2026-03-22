"""
Core language API routes — translate, learn, travel, coach, curriculum, culture.
All routes enforce auth + monthly quota.

Production-safety improvements in this file:
  1. validate_agent_response() is called on every agent result before any DB
     write.  If the agent returns malformed output the request fails with
     HTTP 502 and the bad data never touches the database.
  2. Malformed-output events are logged with task_type, session_id, and a
     truncated sample of the raw data so they can be correlated with agent
     service logs via the shared session_id.
  3. translation history now returns the real DB count via a separate scalar
     query instead of len(items), which was capped at the page limit.
"""

import logging
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import enforce_monthly_quota, get_current_user, get_db, get_user_plan
from app.core.redis_client import increment_monthly_usage
from app.models.models import (
    CoachingSession,
    Lesson,
    LessonProgress,
    Plan,
    TranslationHistory,
    TravelScenario,
    UsageLog,
    User,
)
from app.schemas.agent_outputs import validate_agent_response
from app.services.agent_client import AgentServiceError, get_agent_client

logger = logging.getLogger("avantika.language")

router = APIRouter(prefix="/language", tags=["language"])


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class TranslateRequest(BaseModel):
    input_text: str
    source_language: str = "Hindi"
    target_language: str = "English"
    context_tone: str = "neutral"
    formality_level: str = "neutral"


class LearnRequest(BaseModel):
    source_language: str = "Hindi"
    target_language: str = "English"
    user_level: str = "beginner"
    lesson_topic: str
    session_number: int = 1
    previous_topics: list[str] = []


class TravelRequest(BaseModel):
    destination_country: str
    source_language: str = "Hindi"
    target_language: str
    scenario_type: str   # airport_arrival, hotel_checkin, etc.


class CoachRequest(BaseModel):
    job_field: str
    coaching_type: str  # job_interview, email_writing, etc.
    source_language: str = "Hindi"
    target_language: str = "English"
    user_draft: str | None = None


class CurriculumRequest(BaseModel):
    source_language: str = "Hindi"
    target_language: str = "English"
    user_level: str = "beginner"
    learning_goal: str = "daily_conversation"
    duration_weeks: int = 4


class CultureRequest(BaseModel):
    source_country: str
    destination_country: str
    etiquette_context: str = "general"


class ProgressUpdate(BaseModel):
    exercises_completed: int
    exercises_total: int
    score_percent: float
    time_spent_seconds: int = 0
    mark_completed: bool = False


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------

async def _run_agent(
    task_type: str,
    payload: dict,
    user: User,
    db: AsyncSession,
    plan: Plan,
) -> dict:
    """
    Invoke agent service, validate output schema, log usage, return result data.

    Failure modes:
      - AgentServiceError (timeout, 5xx, unreachable) → HTTP 503
      - ValidationError (malformed agent output)       → HTTP 502
      - Agent-reported failure (success=false)         → HTTP 500
    """
    payload["task_type"] = task_type
    payload["user_id"] = str(user.id)
    # session_id is the per-request tracking key — forwarded to agent service
    # and stored on UsageLog so backend and agent logs can be joined.
    session_id = str(uuid.uuid4())
    payload["session_id"] = session_id

    start = time.monotonic()
    client = get_agent_client()

    # --- Call agent service ---
    try:
        result = await client.run(payload)
    except AgentServiceError as exc:
        latency_ms = int((time.monotonic() - start) * 1000)
        logger.error(
            "agent_service_error",
            extra={
                "task_type": task_type,
                "session_id": session_id,
                "latency_ms": latency_ms,
                "error": str(exc),
            },
        )
        # Log the failure to DB so usage dashboard shows failed requests
        db.add(UsageLog(
            user_id=user.id,
            task_type=task_type,
            latency_ms=latency_ms,
            success=False,
            error_message=str(exc),
            session_id=session_id,
        ))
        await db.commit()
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc

    latency_ms = int((time.monotonic() - start) * 1000)

    # --- Validate agent output before touching the DB ---
    # validate_agent_response raises pydantic.ValidationError if the agent
    # returned structurally invalid data.  This prevents malformed JSON from
    # being persisted and surfaced to users.
    data = result.get("data", {})
    try:
        validate_agent_response(task_type, data)
    except (ValidationError, ValueError) as exc:
        error_summary = str(exc)
        # Log a truncated sample of the raw data for debugging — do not log
        # the full content in case it contains sensitive user text.
        raw_sample = str(data)[:300]
        logger.error(
            "agent_output_validation_failed",
            extra={
                "task_type": task_type,
                "session_id": session_id,
                "error": error_summary,
                "raw_sample": raw_sample,
            },
        )
        # Log the failure — helps admin dashboard show malformed-output rate
        db.add(UsageLog(
            user_id=user.id,
            task_type=task_type,
            latency_ms=latency_ms,
            success=False,
            error_message=f"malformed_output: {error_summary[:200]}",
            session_id=session_id,
        ))
        await db.commit()
        # Return 502 (Bad Gateway) — the upstream (agent service) returned
        # an invalid response.  Include session_id so ops can correlate logs.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "Agent returned malformed output",
                "task_type": task_type,
                "session_id": session_id,
            },
        )

    # --- Increment quota usage in Redis ---
    await increment_monthly_usage(str(user.id))

    # --- Persist usage log ---
    db.add(UsageLog(
        user_id=user.id,
        task_type=task_type,
        model_used=result.get("model_used"),
        tokens_input=result.get("tokens_input", 0),
        tokens_output=result.get("tokens_output", 0),
        latency_ms=latency_ms,
        success=result.get("success", True),
        error_message=result.get("error"),
        session_id=session_id,
    ))
    await db.commit()

    # --- Check agent-reported failure ---
    if not result.get("success"):
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": result.get("error", "Agent task failed"),
                "task_type": task_type,
                "session_id": session_id,
            },
        )

    return data


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/translate")
async def translate(
    body: TranslateRequest,
    user: User = Depends(enforce_monthly_quota),
    plan: Plan = Depends(get_user_plan),
    db: AsyncSession = Depends(get_db),
):
    data = await _run_agent("translate", body.model_dump(), user, db, plan)

    # Extract primary_translation from metadata envelope if present
    content = data.get("content", data)

    db.add(TranslationHistory(
        user_id=user.id,
        source_language=body.source_language,
        target_language=body.target_language,
        input_text=body.input_text,
        output_data=data,
        context_tone=body.context_tone,
        formality_level=body.formality_level,
    ))
    await db.commit()

    return {"success": True, "data": data}


@router.post("/learn")
async def learn(
    body: LearnRequest,
    user: User = Depends(enforce_monthly_quota),
    plan: Plan = Depends(get_user_plan),
    db: AsyncSession = Depends(get_db),
):
    data = await _run_agent("learn", body.model_dump(), user, db, plan)

    lesson = Lesson(
        user_id=user.id,
        source_language=body.source_language,
        target_language=body.target_language,
        user_level=body.user_level,
        topic=body.lesson_topic,
        session_number=body.session_number,
        content=data,
    )
    db.add(lesson)
    await db.commit()
    await db.refresh(lesson)

    return {"success": True, "lesson_id": str(lesson.id), "data": data}


@router.post("/travel/scenario")
async def travel_scenario(
    body: TravelRequest,
    user: User = Depends(enforce_monthly_quota),
    plan: Plan = Depends(get_user_plan),
    db: AsyncSession = Depends(get_db),
):
    if not plan.allow_travel_packs:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Travel packs require Pro plan or higher",
        )

    data = await _run_agent("travel", body.model_dump(), user, db, plan)

    db.add(TravelScenario(
        user_id=user.id,
        destination_country=body.destination_country,
        source_language=body.source_language,
        target_language=body.target_language,
        scenario_type=body.scenario_type,
        output_data=data,
    ))
    await db.commit()

    return {"success": True, "data": data}


@router.post("/coach")
async def professional_coach(
    body: CoachRequest,
    user: User = Depends(enforce_monthly_quota),
    plan: Plan = Depends(get_user_plan),
    db: AsyncSession = Depends(get_db),
):
    if not plan.allow_job_coaching:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Job coaching requires Pro plan or higher",
        )

    data = await _run_agent("coach", body.model_dump(), user, db, plan)

    db.add(CoachingSession(
        user_id=user.id,
        job_field=body.job_field,
        coaching_type=body.coaching_type,
        source_language=body.source_language,
        target_language=body.target_language,
        user_draft=body.user_draft,
        output_data=data,
    ))
    await db.commit()

    return {"success": True, "data": data}


@router.post("/curriculum")
async def plan_curriculum(
    body: CurriculumRequest,
    user: User = Depends(enforce_monthly_quota),
    plan: Plan = Depends(get_user_plan),
    db: AsyncSession = Depends(get_db),
):
    data = await _run_agent("curriculum", body.model_dump(), user, db, plan)
    return {"success": True, "data": data}


@router.post("/culture")
async def cultural_etiquette(
    body: CultureRequest,
    user: User = Depends(enforce_monthly_quota),
    plan: Plan = Depends(get_user_plan),
    db: AsyncSession = Depends(get_db),
):
    data = await _run_agent("culture", body.model_dump(), user, db, plan)
    return {"success": True, "data": data}


# ---------------------------------------------------------------------------
# History and profile
# ---------------------------------------------------------------------------

@router.get("/history/translations")
async def translation_history(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Run count and page queries independently.
    # Previously `total` was len(items) which was capped at `limit`,
    # making pagination impossible on the frontend side.
    total = await db.scalar(
        select(func.count()).where(
            TranslationHistory.user_id == current_user.id
        )
    )
    result = await db.execute(
        select(TranslationHistory)
        .where(TranslationHistory.user_id == current_user.id)
        .order_by(TranslationHistory.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    items = result.scalars().all()
    return {
        "items": [
            {
                "id": str(t.id),
                "input_text": t.input_text,
                "source_language": t.source_language,
                "target_language": t.target_language,
                # Prefer content.primary_translation when metadata envelope present
                "primary_translation": (
                    t.output_data.get("content", t.output_data).get("primary_translation")
                    if isinstance(t.output_data, dict) else None
                ),
                "created_at": t.created_at.isoformat(),
                "is_bookmarked": t.is_bookmarked,
            }
            for t in items
        ],
        "total": total or 0,   # real DB count — not capped by page size
        "limit": limit,
        "offset": offset,
    }


@router.get("/lessons")
async def list_lessons(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    total = await db.scalar(
        select(func.count()).where(Lesson.user_id == current_user.id)
    )
    result = await db.execute(
        select(Lesson)
        .where(Lesson.user_id == current_user.id)
        .order_by(Lesson.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    lessons = result.scalars().all()
    return {
        "total": total or 0,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": str(l.id),
                "topic": l.topic,
                "target_language": l.target_language,
                "source_language": l.source_language,
                "user_level": l.user_level,
                "session_number": l.session_number,
                "is_completed": l.is_completed,
                "score": l.score,
                "created_at": l.created_at.isoformat(),
            }
            for l in lessons
        ],
    }


@router.get("/lessons/{lesson_id}")
async def get_lesson(
    lesson_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return full lesson content — used to resume a lesson mid-session."""
    lesson = await db.get(Lesson, lesson_id)
    if not lesson or lesson.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lesson not found")

    progress = lesson.progress
    return {
        "lesson": {
            "id": str(lesson.id),
            "topic": lesson.topic,
            "target_language": lesson.target_language,
            "source_language": lesson.source_language,
            "user_level": lesson.user_level,
            "session_number": lesson.session_number,
            "content": lesson.content,
            "is_completed": lesson.is_completed,
            "score": lesson.score,
            "created_at": lesson.created_at.isoformat(),
            "progress": {
                "exercises_completed": progress.exercises_completed,
                "exercises_total": progress.exercises_total,
                "score_percent": progress.score_percent,
                "time_spent_seconds": progress.time_spent_seconds,
                "completed_at": progress.completed_at.isoformat() if progress.completed_at else None,
            } if progress else None,
        }
    }


@router.put("/lessons/{lesson_id}/progress")
async def update_lesson_progress(
    lesson_id: uuid.UUID,
    body: ProgressUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upsert lesson progress.  Called on each exercise answer and on completion.
    Ownership is verified — users can only update their own lessons.
    """
    lesson = await db.get(Lesson, lesson_id)
    if not lesson or lesson.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lesson not found")

    if body.exercises_total <= 0:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "exercises_total must be > 0")

    if lesson.progress:
        p = lesson.progress
    else:
        p = LessonProgress(lesson_id=lesson.id, user_id=current_user.id)
        db.add(p)

    p.exercises_completed = body.exercises_completed
    p.exercises_total = body.exercises_total
    p.score_percent = body.score_percent
    p.time_spent_seconds = body.time_spent_seconds

    if body.mark_completed and not lesson.is_completed:
        from datetime import UTC, datetime
        lesson.is_completed = True
        lesson.score = body.score_percent
        p.completed_at = datetime.now(UTC)

    await db.commit()
    return {"updated": True, "lesson_id": str(lesson.id)}


@router.get("/profile/progress")
async def user_progress(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.core.redis_client import get_monthly_usage

    lessons_count = await db.scalar(
        select(func.count()).where(Lesson.user_id == current_user.id)
    )
    completed_lessons = await db.scalar(
        select(func.count()).where(
            Lesson.user_id == current_user.id,
            Lesson.is_completed == True,  # noqa: E712
        )
    )
    translations_count = await db.scalar(
        select(func.count()).where(TranslationHistory.user_id == current_user.id)
    )
    coaching_count = await db.scalar(
        select(func.count()).where(CoachingSession.user_id == current_user.id)
    )
    monthly_usage = await get_monthly_usage(str(current_user.id))

    return {
        "lessons_total": lessons_count or 0,
        "lessons_completed": completed_lessons or 0,
        "translations_total": translations_count or 0,
        "coaching_sessions_total": coaching_count or 0,
        "monthly_requests_used": monthly_usage,
    }

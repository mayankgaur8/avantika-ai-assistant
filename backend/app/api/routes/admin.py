"""
Admin API endpoints — usage analytics, user management, system health.
Requires admin role.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin_user, get_db
from app.models.models import (
    CoachingSession,
    Lesson,
    Plan,
    Subscription,
    SubscriptionStatus,
    TranslationHistory,
    UsageLog,
    User,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/usage")
async def global_usage_stats(
    _=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    total_users = await db.scalar(select(func.count()).select_from(User))
    active_subs = await db.scalar(
        select(func.count()).where(Subscription.status == SubscriptionStatus.active)
    )
    total_requests = await db.scalar(select(func.count()).select_from(UsageLog))
    total_translations = await db.scalar(select(func.count()).select_from(TranslationHistory))
    total_lessons = await db.scalar(select(func.count()).select_from(Lesson))
    total_coaching = await db.scalar(select(func.count()).select_from(CoachingSession))

    # Cost estimate (rough)
    total_tokens = await db.scalar(
        select(func.sum(UsageLog.tokens_input + UsageLog.tokens_output)).select_from(UsageLog)
    ) or 0

    return {
        "total_users": total_users,
        "active_subscriptions": active_subs,
        "total_api_requests": total_requests,
        "total_translations": total_translations,
        "total_lessons": total_lessons,
        "total_coaching_sessions": total_coaching,
        "total_tokens_used": total_tokens,
        "estimated_cost_usd": round(total_tokens * 0.000002, 4),  # rough gpt-4o-mini pricing
    }


@router.get("/users")
async def list_users(
    limit: int = 50,
    offset: int = 0,
    _=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
    )
    users = result.scalars().all()
    return {
        "users": [
            {
                "id": str(u.id),
                "email": u.email,
                "name": u.name,
                "role": u.role.value,
                "is_active": u.is_active,
                "plan": u.subscription.plan.name.value if u.subscription and u.subscription.plan else "free",
                "subscription_status": u.subscription.status.value if u.subscription else None,
                "created_at": u.created_at.isoformat(),
            }
            for u in users
        ]
    }


@router.get("/health")
async def admin_health(_=Depends(get_admin_user)):
    from app.services.agent_client import get_agent_client
    agent_ok = await get_agent_client().health_check()

    return {
        "backend": "ok",
        "agent_service": "ok" if agent_ok else "unavailable",
    }

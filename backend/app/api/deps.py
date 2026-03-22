"""
FastAPI dependency injectors — auth, DB, rate limiting, plan enforcement.
"""

import uuid
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis_client import check_rate_limit, get_monthly_usage
from app.core.security import decode_token
from app.models.models import Plan, PlanName, Subscription, SubscriptionStatus, User


# ---------------------------------------------------------------------------
# Current user
# ---------------------------------------------------------------------------

async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing or invalid Authorization header")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = decode_token(token)
    except ValueError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc

    if payload.get("type") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token type")

    user = await db.get(User, uuid.UUID(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or disabled")

    return user


async def get_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role.value != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin access required")
    return current_user


# ---------------------------------------------------------------------------
# Plan enforcement
# ---------------------------------------------------------------------------

async def get_user_plan(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Plan:
    """Resolve the active plan for the current user."""
    if current_user.subscription and current_user.subscription.status == SubscriptionStatus.active:
        plan = current_user.subscription.plan
        if plan:
            return plan

    result = await db.execute(select(Plan).where(Plan.name == PlanName.free))
    free_plan = result.scalar_one_or_none()
    if not free_plan:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Plan configuration error")
    return free_plan


async def enforce_monthly_quota(
    current_user: User = Depends(get_current_user),
    plan: Plan = Depends(get_user_plan),
) -> User:
    """Raise 429 if the user has exceeded their monthly request quota."""
    usage = await get_monthly_usage(str(current_user.id))
    if usage >= plan.monthly_requests:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "message": "Monthly request limit exceeded",
                "limit": plan.monthly_requests,
                "used": usage,
                "upgrade_url": "/billing/plans",
            },
        )
    return current_user


async def enforce_ip_rate_limit(
    x_forwarded_for: Annotated[str | None, Header()] = None,
) -> None:
    """Enforce a per-IP rate limit of 30 requests/minute for unauthenticated endpoints."""
    ip = x_forwarded_for or "unknown"
    allowed = await check_rate_limit(f"ip:{ip}", limit=30, window_seconds=60)
    if not allowed:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many requests")

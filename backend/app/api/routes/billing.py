"""
Billing and subscription endpoints — checkout, webhook, plan info.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.models import Plan, PlanName, User
from app.services.billing_service import PLAN_CONFIGS, billing_service

router = APIRouter(prefix="/billing", tags=["billing"])


class CheckoutRequest(BaseModel):
    plan_name: PlanName
    billing_period: str = "monthly"   # monthly | yearly


@router.get("/plans")
async def list_plans(db: AsyncSession = Depends(get_db)):
    """Return all active plans with pricing."""
    result = await db.execute(select(Plan).where(Plan.is_active == True))  # noqa: E712
    plans = result.scalars().all()

    return {
        "plans": [
            {
                "id": str(p.id),
                "name": p.name.value,
                "display_name": p.display_name,
                "monthly_price_inr": p.monthly_price_inr // 100,
                "yearly_price_inr": p.yearly_price_inr // 100,
                "monthly_requests": p.monthly_requests,
                "allow_premium_model": p.allow_premium_model,
                "allow_whatsapp": p.allow_whatsapp,
                "allow_voice": p.allow_voice,
                "allow_travel_packs": p.allow_travel_packs,
                "allow_job_coaching": p.allow_job_coaching,
                "features": p.features,
            }
            for p in plans
        ]
    }


@router.post("/checkout")
async def create_checkout(
    body: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create Razorpay subscription checkout session."""
    if body.plan_name == PlanName.free:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot checkout for free plan")

    try:
        session = await billing_service.create_checkout_session(
            current_user, body.plan_name, body.billing_period, db
        )
        return {"success": True, "checkout": session}
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@router.post("/webhook")
async def razorpay_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Razorpay webhook handler — validates HMAC signature and processes events."""
    signature = request.headers.get("X-Razorpay-Signature", "")
    payload_bytes = await request.body()

    try:
        result = await billing_service.handle_webhook(payload_bytes, signature, db)
        return result
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@router.get("/subscription")
async def get_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the current user's active subscription."""
    sub = current_user.subscription
    if not sub:
        return {"subscription": None, "plan": "free"}

    return {
        "subscription": {
            "id": str(sub.id),
            "status": sub.status.value,
            "razorpay_subscription_id": sub.razorpay_subscription_id,
            "current_period_start": sub.current_period_start.isoformat() if sub.current_period_start else None,
            "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
        },
        "plan": {
            "name": sub.plan.name.value if sub.plan else "free",
            "display_name": sub.plan.display_name if sub.plan else "Free",
        },
    }

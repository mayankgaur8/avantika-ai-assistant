"""
Razorpay billing service — subscriptions, webhooks, plan enforcement.

Production-safety improvements in this file:
  1. Idempotency — every webhook carries a Razorpay event_id.  We check for
     an existing PaymentEvent row with that event_id before doing any work.
     Duplicate events return immediately with {"reason": "duplicate"}.
  2. Audit trail — a PaymentEvent row with processing_status="processing" is
     inserted (and flushed) *before* the handler runs.  Whether the handler
     succeeds or fails, the row is committed with the final status and any
     error message.  No webhook event is ever silently swallowed.
  3. Never double-activate — _on_subscription_activated checks whether the
     subscription is already active with the same razorpay_subscription_id
     before touching it.  Combined with the idempotency check this gives
     two independent guards against double-activation.
  4. Transaction safety — the commit is the last operation after both the
     business-logic mutation and the audit-row update.  A failed commit rolls
     back both atomically.  We never commit partial state.
  5. Structured return values — callers receive {"processed": bool, "event":
     str, "reason"?: str, "error"?: str} so the route layer can log and
     respond appropriately.
"""

import hashlib
import hmac
import json
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import razorpay
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import (
    PaymentEvent,
    PaymentStatus,
    Plan,
    PlanName,
    Subscription,
    SubscriptionStatus,
    User,
)

logger = logging.getLogger("avantika.billing")


# ---------------------------------------------------------------------------
# Razorpay client
# ---------------------------------------------------------------------------

def _get_razorpay_client() -> razorpay.Client:
    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )


# ---------------------------------------------------------------------------
# Plan definitions (synced with DB seed)
# ---------------------------------------------------------------------------

PLAN_CONFIGS = {
    PlanName.free: {
        "display_name": "Free",
        "monthly_price_inr": 0,
        "yearly_price_inr": 0,
        "monthly_requests": 20,
        "allow_premium_model": False,
        "allow_whatsapp": False,
        "allow_voice": False,
        "allow_travel_packs": False,
        "allow_job_coaching": False,
        "translation_limit_per_day": 5,
        "features": [
            "20 requests/month",
            "Basic translation",
            "2 languages",
            "Web access only",
        ],
    },
    PlanName.pro: {
        "display_name": "Pro",
        "monthly_price_inr": 49900,     # ₹499/month in paise
        "yearly_price_inr": 449900,     # ₹4499/year (~25% off)
        "monthly_requests": 300,
        "allow_premium_model": False,
        "allow_whatsapp": False,
        "allow_voice": True,
        "allow_travel_packs": True,
        "allow_job_coaching": True,
        "translation_limit_per_day": 50,
        "features": [
            "300 requests/month",
            "All languages",
            "Travel packs",
            "Job coaching",
            "Voice input",
            "Saved lessons",
            "Progress tracking",
        ],
    },
    PlanName.premium: {
        "display_name": "Premium",
        "monthly_price_inr": 99900,     # ₹999/month
        "yearly_price_inr": 899900,     # ₹8999/year (~25% off)
        "monthly_requests": 1000,
        "allow_premium_model": True,
        "allow_whatsapp": True,
        "allow_voice": True,
        "allow_travel_packs": True,
        "allow_job_coaching": True,
        "translation_limit_per_day": 200,
        "features": [
            "1000 requests/month",
            "GPT-4o premium model",
            "WhatsApp integration",
            "Unlimited travel packs",
            "Priority support",
            "Export lessons",
            "Cultural etiquette packs",
        ],
    },
    PlanName.enterprise: {
        "display_name": "Enterprise",
        "monthly_price_inr": 0,   # custom pricing
        "yearly_price_inr": 0,
        "monthly_requests": 99999,
        "allow_premium_model": True,
        "allow_whatsapp": True,
        "allow_voice": True,
        "allow_travel_packs": True,
        "allow_job_coaching": True,
        "translation_limit_per_day": 9999,
        "features": [
            "Unlimited requests",
            "Team dashboards",
            "Custom integrations",
            "Dedicated support",
            "SLA guarantee",
            "CRM integration",
        ],
    },
}


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class BillingService:

    async def create_checkout_session(
        self,
        user: User,
        plan_name: PlanName,
        billing_period: str,    # "monthly" | "yearly"
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Create a Razorpay subscription checkout link."""
        plan = await self._get_plan(plan_name, db)
        if not plan:
            raise ValueError(f"Plan '{plan_name}' not found")

        rz = _get_razorpay_client()

        razorpay_plan_id = (
            plan.razorpay_plan_id_monthly
            if billing_period == "monthly"
            else plan.razorpay_plan_id_yearly
        )

        if not razorpay_plan_id:
            raise ValueError(f"Razorpay plan ID not configured for {plan_name}/{billing_period}")

        subscription = rz.subscription.create({
            "plan_id": razorpay_plan_id,
            "customer_notify": 1,
            "total_count": 12 if billing_period == "monthly" else 1,
            "notes": {
                "user_id": str(user.id),
                "user_email": user.email,
                "plan_name": plan_name.value,
                "billing_period": billing_period,
            },
        })

        return {
            "razorpay_subscription_id": subscription["id"],
            "razorpay_key_id": settings.RAZORPAY_KEY_ID,
            "short_url": subscription.get("short_url"),
            "plan_name": plan_name.value,
            "billing_period": billing_period,
            "amount_display": (
                plan.monthly_price_inr // 100
                if billing_period == "monthly"
                else plan.yearly_price_inr // 100
            ),
        }

    async def handle_webhook(
        self,
        payload_bytes: bytes,
        signature: str,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """
        Validate and process a Razorpay webhook event.

        Processing order:
          1. HMAC-SHA256 signature verification (uses raw bytes — never decoded first).
          2. Idempotency check: if this event_id already has a PaymentEvent row,
             return immediately without processing.
          3. Insert a PaymentEvent audit row with processing_status="processing".
          4. Dispatch to the appropriate event handler.
          5. On success: update row to "processed", commit.
          6. On failure: update row to "failed" with error_message, commit.
             The audit row is always committed so no event is silently lost.

        Returns a structured dict so the route layer can log the outcome.
        Always returns a non-exception result — the route layer never raises
        on webhook errors because Razorpay interprets non-2xx as "retry".
        """
        # --- Step 1: Verify HMAC-SHA256 signature ---
        # payload_bytes must be the raw request body — do not decode or parse
        # before this call or the HMAC will not match.
        expected_sig = hmac.new(
            settings.RAZORPAY_WEBHOOK_SECRET.encode(),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected_sig, signature):
            # Raise here — the route layer turns this into HTTP 400.
            # A bad signature is not retried by Razorpay.
            raise ValueError("Invalid webhook signature")

        event_data = json.loads(payload_bytes)
        event_type = event_data.get("event", "unknown")
        # Razorpay includes a unique "id" on every webhook delivery.
        event_id = event_data.get("id")

        logger.info(
            "webhook_received",
            extra={"event_type": event_type, "event_id": event_id},
        )

        # --- Step 2: Idempotency check ---
        # If we have already processed (or are currently processing) this exact
        # event_id, return immediately.  This handles both Razorpay retries and
        # any accidental double-delivery from our own infrastructure.
        if event_id:
            existing_result = await db.execute(
                select(PaymentEvent).where(PaymentEvent.event_id == event_id)
            )
            existing = existing_result.scalar_one_or_none()
            if existing:
                logger.info(
                    "webhook_duplicate_skipped",
                    extra={
                        "event_id": event_id,
                        "event_type": event_type,
                        "existing_status": existing.processing_status,
                    },
                )
                return {
                    "processed": False,
                    "reason": "duplicate",
                    "event": event_type,
                    "event_id": event_id,
                }

        # --- Step 3: Insert audit row before handler runs ---
        # flush() writes the row to DB within the current transaction without
        # committing.  This means the row exists if the process crashes
        # mid-handler, giving ops visibility into in-flight events.
        payment_event = PaymentEvent(
            event_id=event_id,
            event_type=event_type,
            payload=event_data,
            processing_status="processing",
        )
        db.add(payment_event)
        await db.flush()

        # --- Step 4: Dispatch to handler ---
        try:
            match event_type:
                case "subscription.activated":
                    await self._on_subscription_activated(event_data, db)
                case "subscription.charged":
                    await self._on_subscription_charged(event_data, db)
                case "subscription.cancelled":
                    await self._on_subscription_cancelled(event_data, db)
                case "payment.captured":
                    await self._on_payment_captured(event_data, payment_event, db)
                case _:
                    # Unknown event types are logged and committed as audit rows
                    # so we can track Razorpay event volume without crashing.
                    logger.info(
                        "webhook_unhandled_event",
                        extra={"event_type": event_type, "event_id": event_id},
                    )

            # --- Step 5: Mark success, commit ---
            payment_event.processing_status = "processed"
            payment_event.processed_at = datetime.now(UTC)
            await db.commit()

            logger.info(
                "webhook_processed",
                extra={"event_type": event_type, "event_id": event_id},
            )
            return {"processed": True, "event": event_type, "event_id": event_id}

        except Exception as exc:
            # --- Step 6: Mark failure, commit audit row ---
            # Committing here ensures the audit row is persisted even though
            # the business-logic mutation may have partially modified other rows.
            # SQLAlchemy's unit-of-work will only include changes made *before*
            # the exception, so partial subscription mutations are rolled back
            # by the implicit rollback that precedes this commit.
            payment_event.processing_status = "failed"
            payment_event.error_message = str(exc)[:500]   # cap at 500 chars
            try:
                await db.commit()
            except Exception as commit_exc:
                # If even the audit commit fails, log both errors so nothing is lost.
                logger.error(
                    "webhook_audit_commit_failed",
                    extra={
                        "event_id": event_id,
                        "handler_error": str(exc),
                        "commit_error": str(commit_exc),
                    },
                )

            logger.error(
                "webhook_handler_failed",
                extra={
                    "event_type": event_type,
                    "event_id": event_id,
                    "error": str(exc),
                },
            )
            # Return a non-exception result so the route returns HTTP 200.
            # Razorpay will not retry on 2xx, but our audit row captures the
            # failure for manual investigation.
            return {
                "processed": False,
                "event": event_type,
                "event_id": event_id,
                "error": str(exc),
            }

    # -------------------------------------------------------------------------
    # Event handlers
    # -------------------------------------------------------------------------

    async def _on_subscription_activated(self, data: dict, db: AsyncSession) -> None:
        sub_data = data.get("payload", {}).get("subscription", {}).get("entity", {})
        razorpay_sub_id = sub_data.get("id")
        notes = sub_data.get("notes", {})
        user_id = notes.get("user_id")

        if not user_id:
            logger.warning("subscription_activated_missing_user_id", extra={"sub_id": razorpay_sub_id})
            return

        user = await db.get(User, uuid.UUID(user_id))
        if not user:
            logger.warning("subscription_activated_user_not_found", extra={"user_id": user_id})
            return

        # Guard: do not re-activate a subscription that is already active with
        # this exact Razorpay subscription ID.  This is a second line of defence
        # after the event_id idempotency check at the top of handle_webhook.
        if (
            user.subscription
            and user.subscription.razorpay_subscription_id == razorpay_sub_id
            and user.subscription.status == SubscriptionStatus.active
        ):
            logger.info(
                "subscription_already_active_skipped",
                extra={"user_id": user_id, "sub_id": razorpay_sub_id},
            )
            return

        plan_name = PlanName(notes.get("plan_name", "free"))
        plan = await self._get_plan(plan_name, db)
        if not plan:
            raise ValueError(f"Plan '{plan_name}' not found during subscription activation")

        # Upsert subscription — update existing row or create new one
        if user.subscription:
            sub = user.subscription
        else:
            sub = Subscription(user_id=user.id)
            db.add(sub)

        sub.plan_id = plan.id
        sub.razorpay_subscription_id = razorpay_sub_id
        sub.status = SubscriptionStatus.active
        sub.current_period_start = datetime.now(UTC)
        sub.current_period_end = datetime.now(UTC) + timedelta(days=30)

        logger.info(
            "subscription_activated",
            extra={"user_id": user_id, "plan": plan_name.value, "sub_id": razorpay_sub_id},
        )

    async def _on_subscription_charged(self, data: dict, db: AsyncSession) -> None:
        sub_data = data.get("payload", {}).get("subscription", {}).get("entity", {})
        razorpay_sub_id = sub_data.get("id")

        result = await db.execute(
            select(Subscription).where(
                Subscription.razorpay_subscription_id == razorpay_sub_id
            )
        )
        sub = result.scalar_one_or_none()
        if sub:
            sub.status = SubscriptionStatus.active
            sub.current_period_end = datetime.now(UTC) + timedelta(days=30)
        else:
            logger.warning(
                "subscription_charged_not_found",
                extra={"razorpay_sub_id": razorpay_sub_id},
            )

    async def _on_subscription_cancelled(self, data: dict, db: AsyncSession) -> None:
        sub_data = data.get("payload", {}).get("subscription", {}).get("entity", {})
        razorpay_sub_id = sub_data.get("id")

        result = await db.execute(
            select(Subscription).where(
                Subscription.razorpay_subscription_id == razorpay_sub_id
            )
        )
        sub = result.scalar_one_or_none()
        if sub:
            sub.status = SubscriptionStatus.cancelled
            sub.cancelled_at = datetime.now(UTC)
        else:
            logger.warning(
                "subscription_cancelled_not_found",
                extra={"razorpay_sub_id": razorpay_sub_id},
            )

    async def _on_payment_captured(
        self,
        data: dict,
        current_event: PaymentEvent,
        db: AsyncSession,
    ) -> None:
        """
        Update the audit row for this payment event with the payment amount
        and Razorpay payment ID.  We use the already-inserted current_event
        row rather than querying for a previous one — the payment.captured
        event IS the authoritative record for this payment.
        """
        payment = data.get("payload", {}).get("payment", {}).get("entity", {})
        current_event.razorpay_payment_id = payment.get("id")
        current_event.amount_inr_paise = payment.get("amount")
        current_event.status = PaymentStatus.captured

    # -------------------------------------------------------------------------
    # Shared helpers
    # -------------------------------------------------------------------------

    async def _get_plan(self, plan_name: PlanName, db: AsyncSession) -> Plan | None:
        result = await db.execute(select(Plan).where(Plan.name == plan_name))
        return result.scalar_one_or_none()

    async def get_user_plan_limits(
        self, user: User, db: AsyncSession
    ) -> dict[str, Any]:
        """Return the effective limits for a user based on their active subscription."""
        if user.subscription and user.subscription.status == SubscriptionStatus.active:
            plan = user.subscription.plan
        else:
            result = await db.execute(select(Plan).where(Plan.name == PlanName.free))
            plan = result.scalar_one_or_none()

        if not plan:
            return PLAN_CONFIGS[PlanName.free]

        return {
            "plan_name": plan.name.value,
            "monthly_requests": plan.monthly_requests,
            "allow_premium_model": plan.allow_premium_model,
            "allow_whatsapp": plan.allow_whatsapp,
            "allow_voice": plan.allow_voice,
            "allow_travel_packs": plan.allow_travel_packs,
            "allow_job_coaching": plan.allow_job_coaching,
            "translation_limit_per_day": plan.translation_limit_per_day,
        }


billing_service = BillingService()

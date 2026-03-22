"""
Authentication service — register, login, token refresh.
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.models import Plan, PlanName, Subscription, SubscriptionStatus, User


class AuthError(Exception):
    pass


class AuthService:

    async def register(
        self,
        email: str,
        name: str,
        password: str,
        db: AsyncSession,
    ) -> dict:
        # Check duplicate
        result = await db.execute(select(User).where(User.email == email.lower()))
        if result.scalar_one_or_none():
            raise AuthError("Email already registered")

        user = User(
            email=email.lower(),
            name=name,
            password_hash=hash_password(password),
        )
        db.add(user)
        await db.flush()

        # Assign free plan subscription
        plan_result = await db.execute(select(Plan).where(Plan.name == PlanName.free))
        free_plan = plan_result.scalar_one_or_none()
        if free_plan:
            sub = Subscription(
                user_id=user.id,
                plan_id=free_plan.id,
                status=SubscriptionStatus.active,
            )
            db.add(sub)

        await db.commit()
        await db.refresh(user)

        return self._tokens(user)

    async def login(self, email: str, password: str, db: AsyncSession) -> dict:
        result = await db.execute(select(User).where(User.email == email.lower()))
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.password_hash):
            raise AuthError("Invalid email or password")

        if not user.is_active:
            raise AuthError("Account is disabled")

        return self._tokens(user)

    async def refresh(self, refresh_token: str, db: AsyncSession) -> dict:
        try:
            payload = decode_token(refresh_token)
        except ValueError as exc:
            raise AuthError(str(exc)) from exc

        if payload.get("type") != "refresh":
            raise AuthError("Invalid token type")

        user = await db.get(User, payload["sub"])
        if not user or not user.is_active:
            raise AuthError("User not found or disabled")

        return self._tokens(user)

    @staticmethod
    def _tokens(user: User) -> dict:
        return {
            "access_token": create_access_token(str(user.id), {"role": user.role.value}),
            "refresh_token": create_refresh_token(str(user.id)),
            "token_type": "bearer",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "name": user.name,
                "role": user.role.value,
            },
        }


auth_service = AuthService()

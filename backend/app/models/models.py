"""
SQLAlchemy ORM models — full database schema.
"""

import uuid
from datetime import UTC, datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


def now_utc():
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class UserRole(str, PyEnum):
    user = "user"
    admin = "admin"
    enterprise = "enterprise"


class PlanName(str, PyEnum):
    free = "free"
    pro = "pro"
    premium = "premium"
    enterprise = "enterprise"


class SubscriptionStatus(str, PyEnum):
    active = "active"
    cancelled = "cancelled"
    expired = "expired"
    trialing = "trialing"
    past_due = "past_due"


class TaskTypeEnum(str, PyEnum):
    translate = "translate"
    learn = "learn"
    travel = "travel"
    coach = "coach"
    curriculum = "curriculum"
    culture = "culture"


class PaymentStatus(str, PyEnum):
    pending = "pending"
    captured = "captured"
    failed = "failed"
    refunded = "refunded"


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.user, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_email_verified = Column(Boolean, default=False, nullable=False)
    preferred_source_language = Column(String(50), default="Hindi")
    preferred_target_language = Column(String(50), default="English")
    preferred_level = Column(String(20), default="beginner")
    avatar_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_utc)
    updated_at = Column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    # Relationships
    subscription = relationship("Subscription", back_populates="user", uselist=False)
    usage_logs = relationship("UsageLog", back_populates="user")
    lessons = relationship("Lesson", back_populates="user")
    coaching_sessions = relationship("CoachingSession", back_populates="user")
    translation_history = relationship("TranslationHistory", back_populates="user")


# ---------------------------------------------------------------------------
# Plans
# ---------------------------------------------------------------------------

class Plan(Base):
    __tablename__ = "plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Enum(PlanName), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    monthly_price_inr = Column(Integer, nullable=False)   # in paise
    yearly_price_inr = Column(Integer, nullable=False)    # in paise
    monthly_requests = Column(Integer, nullable=False)
    allow_premium_model = Column(Boolean, default=False)
    allow_whatsapp = Column(Boolean, default=False)
    allow_voice = Column(Boolean, default=False)
    allow_travel_packs = Column(Boolean, default=False)
    allow_job_coaching = Column(Boolean, default=False)
    translation_limit_per_day = Column(Integer, default=10)
    razorpay_plan_id_monthly = Column(String(100), nullable=True)
    razorpay_plan_id_yearly = Column(String(100), nullable=True)
    features = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    subscriptions = relationship("Subscription", back_populates="plan")


# ---------------------------------------------------------------------------
# Subscriptions
# ---------------------------------------------------------------------------

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("plans.id"), nullable=False)
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.trialing)
    razorpay_subscription_id = Column(String(100), nullable=True, index=True)
    razorpay_customer_id = Column(String(100), nullable=True)
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    trial_end = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_utc)
    updated_at = Column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    user = relationship("User", back_populates="subscription")
    plan = relationship("Plan", back_populates="subscriptions")


# ---------------------------------------------------------------------------
# Payment Events
# ---------------------------------------------------------------------------

class PaymentEvent(Base):
    __tablename__ = "payment_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Razorpay's own unique event ID (from the webhook payload "id" field).
    # Used as the idempotency key — a UNIQUE constraint ensures replayed
    # webhooks with the same event_id are rejected at the DB level even if
    # the application-level check is bypassed under race conditions.
    event_id = Column(String(100), nullable=True, unique=True, index=True)

    razorpay_payment_id = Column(String(100), nullable=True, index=True)
    razorpay_order_id = Column(String(100), nullable=True)
    razorpay_subscription_id = Column(String(100), nullable=True)
    event_type = Column(String(100), nullable=False)   # payment.captured, subscription.activated
    amount_inr_paise = Column(Integer, nullable=True)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.pending)

    # Lifecycle tracking for audit purposes.
    # "processing" → row was inserted but handler has not finished.
    # "processed"  → handler completed successfully, subscription state updated.
    # "failed"     → handler raised an exception; error_message holds details.
    # "duplicate"  → event_id was already seen; row not re-processed.
    processing_status = Column(String(20), default="processing", nullable=False)

    # Human-readable failure reason written when processing_status = "failed".
    # Kept short (first 500 chars of the exception message) to stay within
    # the text column without truncation issues.
    error_message = Column(Text, nullable=True)

    payload = Column(JSON, default=dict)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_utc)


# ---------------------------------------------------------------------------
# Usage Logs
# ---------------------------------------------------------------------------

class UsageLog(Base):
    __tablename__ = "usage_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    task_type = Column(Enum(TaskTypeEnum), nullable=False)
    model_used = Column(String(50), nullable=True)
    tokens_input = Column(Integer, default=0)
    tokens_output = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    latency_ms = Column(Integer, default=0)
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    session_id = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_utc, index=True)

    user = relationship("User", back_populates="usage_logs")


# ---------------------------------------------------------------------------
# Lessons
# ---------------------------------------------------------------------------

class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    source_language = Column(String(50), nullable=False)
    target_language = Column(String(50), nullable=False)
    user_level = Column(String(20), nullable=False)
    topic = Column(String(255), nullable=False)
    session_number = Column(Integer, default=1)
    content = Column(JSON, nullable=False)   # full structured lesson JSON
    is_completed = Column(Boolean, default=False)
    score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    user = relationship("User", back_populates="lessons")
    progress = relationship("LessonProgress", back_populates="lesson", uselist=False)


class LessonProgress(Base):
    __tablename__ = "lesson_progress"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("lessons.id"), nullable=False, unique=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    exercises_completed = Column(Integer, default=0)
    exercises_total = Column(Integer, default=0)
    score_percent = Column(Float, default=0.0)
    time_spent_seconds = Column(Integer, default=0)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    lesson = relationship("Lesson", back_populates="progress")


# ---------------------------------------------------------------------------
# Translation History
# ---------------------------------------------------------------------------

class TranslationHistory(Base):
    __tablename__ = "translation_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    source_language = Column(String(50), nullable=False)
    target_language = Column(String(50), nullable=False)
    input_text = Column(Text, nullable=False)
    output_data = Column(JSON, nullable=False)   # full translation JSON
    context_tone = Column(String(50), default="neutral")
    formality_level = Column(String(20), default="neutral")
    is_bookmarked = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=now_utc, index=True)

    user = relationship("User", back_populates="translation_history")


# ---------------------------------------------------------------------------
# Coaching Sessions
# ---------------------------------------------------------------------------

class CoachingSession(Base):
    __tablename__ = "coaching_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    job_field = Column(String(100), nullable=False)
    coaching_type = Column(String(100), nullable=False)
    source_language = Column(String(50), nullable=False)
    target_language = Column(String(50), nullable=False)
    user_draft = Column(Text, nullable=True)
    output_data = Column(JSON, nullable=False)
    is_saved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    user = relationship("User", back_populates="coaching_sessions")


# ---------------------------------------------------------------------------
# Travel Scenarios
# ---------------------------------------------------------------------------

class TravelScenario(Base):
    __tablename__ = "travel_scenarios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    destination_country = Column(String(100), nullable=False)
    source_language = Column(String(50), nullable=False)
    target_language = Column(String(50), nullable=False)
    scenario_type = Column(String(100), nullable=False)
    output_data = Column(JSON, nullable=False)
    is_saved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=now_utc)


# ---------------------------------------------------------------------------
# Phrasebook
# ---------------------------------------------------------------------------

class PhrasebookEntry(Base):
    __tablename__ = "phrasebook_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    source_language = Column(String(50), nullable=False)
    target_language = Column(String(50), nullable=False)
    phrase = Column(Text, nullable=False)
    translation = Column(Text, nullable=False)
    pronunciation = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)   # greetings, travel, business...
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    __table_args__ = (
        UniqueConstraint("user_id", "phrase", "target_language", name="uq_phrase_per_user"),
    )


# ---------------------------------------------------------------------------
# Languages & Countries reference tables
# ---------------------------------------------------------------------------

class Language(Base):
    __tablename__ = "languages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), unique=True, nullable=False)    # e.g. "hi", "de", "fr"
    name = Column(String(100), nullable=False)
    native_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)


class Country(Base):
    __tablename__ = "countries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(5), unique=True, nullable=False)     # ISO alpha-2
    name = Column(String(100), nullable=False)
    primary_language_code = Column(String(10), nullable=True)
    is_active = Column(Boolean, default=True)


# ---------------------------------------------------------------------------
# Automation Runs
# ---------------------------------------------------------------------------

class AutomationRun(Base):
    __tablename__ = "automation_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    run_type = Column(String(100), nullable=False)   # scheduled_lesson, daily_word, etc.
    status = Column(String(20), default="pending")   # pending, running, done, failed
    payload = Column(JSON, default=dict)
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_utc)

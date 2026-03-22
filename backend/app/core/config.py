"""
Central configuration — all settings loaded from environment variables.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    APP_NAME: str = "Avantika Global Language AI"
    ENV: Literal["development", "staging", "production"] = "development"
    SECRET_KEY: str = "change-me-in-production"
    DEBUG: bool = False

    # Backend
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    API_PREFIX: str = "/api/v1"
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://avantika:avantika@localhost:5432/avantika"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_SESSION_TTL: int = 86400      # 24 hours
    REDIS_CACHE_TTL: int = 3600         # 1 hour
    REDIS_RATE_LIMIT_TTL: int = 60      # 1 minute window

    # Agent service (internal)
    AGENT_SERVICE_URL: str = "http://localhost:8001"
    AGENT_SERVICE_INTERNAL_KEY: str = "internal-key-change-me"
    AGENT_TIMEOUT_SECONDS: int = 120

    # Shared AI Platform
    AI_PLATFORM_URL: str = ""
    AI_PLATFORM_APP_KEY: str = ""
    CHEAP_MODEL: str = "gpt-4o-mini"
    PREMIUM_MODEL: str = "gpt-4o"
    USE_LOCAL_MODEL: bool = False
    LOCAL_MODEL: str = "ollama/llama3"

    # OpenAI (fallback if no shared platform)
    OPENAI_API_KEY: str = ""

    # Serper (web search for agents)
    SERPER_API_KEY: str = ""

    # Razorpay
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""

    # JWT
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Plans (request limits per month)
    FREE_PLAN_MONTHLY_REQUESTS: int = 20
    PRO_PLAN_MONTHLY_REQUESTS: int = 300
    PREMIUM_PLAN_MONTHLY_REQUESTS: int = 1000

    # Admin
    ADMIN_EMAIL: str = "admin@avantika.ai"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

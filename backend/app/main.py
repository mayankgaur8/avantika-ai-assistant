"""
Avantika Global Language AI — Backend API
FastAPI application entry point with full middleware, routing, and health checks.
"""

import logging
import time
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import admin, auth, automation, billing, language
from app.core.config import settings
from app.core.database import engine
from app.core.redis_client import close_redis, get_redis
from app.models.models import Base

logger = logging.getLogger(__name__)

startup_state = {
    "database": "pending",
    "redis": "pending",
}


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Startup begin")

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        startup_state["database"] = "ok"
        logger.info("Database startup complete")
    except Exception:
        startup_state["database"] = "failed"
        logger.exception("Database startup failed")

    try:
        await get_redis()
        startup_state["redis"] = "ok"
        logger.info("Redis startup complete")
    except Exception:
        startup_state["redis"] = "failed"
        logger.exception("Redis startup failed")

    logger.info("Startup complete")
    yield

    try:
        await close_redis()
    except Exception:
        logger.exception("Redis shutdown failed")

    try:
        await engine.dispose()
    except Exception:
        logger.exception("Database shutdown failed")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Avantika AI Assistant API",
    description="AI-powered multilingual learning and translation SaaS platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENV != "production" else None,
    redoc_url="/redoc" if settings.ENV != "production" else None,
)


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request timing middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    duration_ms = int((time.monotonic() - start) * 1000)
    response.headers["X-Process-Time-Ms"] = str(duration_ms)
    return response


# ---------------------------------------------------------------------------
# Global exception handler
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if settings.DEBUG:
        raise exc
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error", "detail": str(exc) if settings.ENV != "production" else None},
    )


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

prefix = settings.API_PREFIX

app.include_router(auth.router, prefix=prefix)
app.include_router(language.router, prefix=prefix)
app.include_router(billing.router, prefix=prefix)
app.include_router(admin.router, prefix=prefix)
app.include_router(automation.router, prefix=prefix)


# ---------------------------------------------------------------------------
# Health and readiness probes
# ---------------------------------------------------------------------------

@app.get("/", tags=["ops"])
async def root():
    return {"status": "ok", "service": "avantika-ai-assistant-api"}


@app.get("/health", tags=["ops"])
async def health():
    return {"status": "healthy"}


@app.get("/ready", tags=["ops"])
async def ready():
    # Check Redis
    try:
        r = await get_redis()
        await r.ping()
        redis_ok = True
    except Exception:
        redis_ok = False

    # Check agent service
    from app.services.agent_client import get_agent_client
    agent_ok = await get_agent_client().health_check()

    all_ok = redis_ok and agent_ok
    return JSONResponse(
        status_code=200 if all_ok else 503,
        content={
            "status": "ready" if all_ok else "degraded",
            "startup": startup_state,
            "redis": "ok" if redis_ok else "unavailable",
            "agent_service": "ok" if agent_ok else "unavailable",
        },
    )


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=settings.ENV == "development",
        log_level="info",
    )

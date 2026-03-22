"""
Avantika Language AI — Agent Service Entry Point
Runs as a standalone FastAPI microservice called internally by the backend API.

Production-safety improvements in this file:
  1. X-Internal-Key validation on POST /run — unauthorized callers receive 401.
  2. X-Request-ID is read from the incoming request header and included in all
     log lines for this request, making cross-service traces joinable.
  3. crew_instance.run() is synchronous (CrewAI/LiteLLM blocks threads).
     It is dispatched via run_in_executor so the async event loop is never
     blocked and the service can handle concurrent health-checks while a
     long-running agent task is in flight.
  4. All error paths return a structured JSON body with request_id so the
     backend can surface it to callers without losing context.
"""

import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager
from functools import partial

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from crew import AgentInput, AgentOutput, AvantikaLanguageCrew

logger = logging.getLogger("avantika.agent_service")

# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

crew_instance: AvantikaLanguageCrew | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global crew_instance
    crew_instance = AvantikaLanguageCrew()
    logger.info("agent_service_ready")
    yield
    crew_instance = None


app = FastAPI(
    title="Avantika Language AI — Agent Service",
    description="Internal CrewAI orchestration service — not public-facing",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if os.getenv("ENV") != "production" else None,
)

app.add_middleware(
    CORSMiddleware,
    # In production, restrict to the backend service IP / VNet range via env var.
    allow_origins=os.getenv("AGENT_ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Internal shared key — must match AGENT_SERVICE_INTERNAL_KEY in backend .env
_INTERNAL_KEY: str = os.getenv("AGENT_SERVICE_INTERNAL_KEY", "")


def _get_request_id(request: Request) -> str:
    """
    Return the X-Request-ID supplied by the backend, or mint a new UUID.
    A new UUID is only generated as a fallback — normally the backend always
    propagates the request ID so traces are joinable across services.
    """
    return request.headers.get("X-Request-ID", str(uuid.uuid4()))


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok", "service": "agent-service"}


@app.get("/ready")
async def ready():
    if crew_instance is None:
        raise HTTPException(503, "Crew not initialized")
    return {"status": "ready"}


@app.post("/run", response_model=AgentOutput)
async def run_agent(payload: AgentInput, request: Request) -> AgentOutput:
    """
    Execute a CrewAI agent task. Called exclusively by the backend API.
    This endpoint must never be exposed to the public internet.

    Security:
      - Requires X-Internal-Key header matching AGENT_SERVICE_INTERNAL_KEY.
      - Returns 401 (not 403) so the caller cannot distinguish "wrong key"
        from "endpoint does not exist", reducing information leakage.

    Concurrency:
      - crew_instance.run() is CPU/IO-bound synchronous code (LiteLLM +
        CrewAI call out to OpenAI synchronously).
      - run_in_executor offloads it to the default ThreadPoolExecutor so
        the FastAPI event loop stays free for health checks and other requests
        that arrive while the LLM is streaming its response.
    """
    request_id = _get_request_id(request)

    # --- Step 1: Validate internal key ---
    # Read once; empty string means the env var is not configured — deny all.
    provided_key = request.headers.get("X-Internal-Key", "")
    if not _INTERNAL_KEY or provided_key != _INTERNAL_KEY:
        logger.warning(
            "agent_run_unauthorized",
            extra={"request_id": request_id, "path": "/run"},
        )
        return JSONResponse(
            status_code=401,
            content={
                "error": "Unauthorized",
                "request_id": request_id,
            },
        )

    # --- Step 2: Guard on crew readiness ---
    if crew_instance is None:
        logger.error("agent_run_crew_not_ready", extra={"request_id": request_id})
        return JSONResponse(
            status_code=503,
            content={
                "error": "Agent service not ready — crew not initialized",
                "request_id": request_id,
            },
        )

    logger.info(
        "agent_run_start",
        extra={
            "request_id": request_id,
            "task_type": payload.task_type,
            "source_language": payload.source_language,
            "target_language": payload.target_language,
        },
    )

    # --- Step 3: Run synchronous crew code off the event loop ---
    # partial() binds the payload argument so run_in_executor receives a
    # zero-argument callable, as required.
    loop = asyncio.get_running_loop()
    try:
        result: AgentOutput = await loop.run_in_executor(
            None,                          # default ThreadPoolExecutor
            partial(crew_instance.run, payload),
        )
    except Exception as exc:
        # Unexpected exception from crew itself (not an AgentOutput failure).
        logger.error(
            "agent_run_exception",
            extra={"request_id": request_id, "task_type": payload.task_type, "error": str(exc)},
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "Agent execution failed unexpectedly",
                "detail": str(exc),
                "request_id": request_id,
            },
        )

    log_level = logging.INFO if result.success else logging.WARNING
    logger.log(
        log_level,
        "agent_run_complete",
        extra={
            "request_id": request_id,
            "task_type": payload.task_type,
            "success": result.success,
            "error": result.error,
        },
    )

    return result


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("AGENT_SERVICE_PORT", "8001")),
        reload=os.getenv("ENV") == "development",
        log_level="info",
    )

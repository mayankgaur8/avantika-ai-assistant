"""
HTTP client for the internal Agent Service (CrewAI).
The backend never calls LLMs directly — it routes through the agent service.
"""

import time
from typing import Any

import httpx

from app.core.config import settings


class AgentServiceError(Exception):
    pass


class AgentClient:
    """Thin async HTTP client wrapping the CrewAI agent microservice."""

    def __init__(self):
        self._base_url = settings.AGENT_SERVICE_URL
        self._timeout = settings.AGENT_TIMEOUT_SECONDS
        self._headers = {
            "X-Internal-Key": settings.AGENT_SERVICE_INTERNAL_KEY,
            "Content-Type": "application/json",
        }

    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                headers=self._headers,
                timeout=self._timeout,
            ) as client:
                response = await client.post("/run", json=payload)
                response.raise_for_status()
                result = response.json()
                result["_latency_ms"] = int((time.monotonic() - start) * 1000)
                return result

        except httpx.TimeoutException as exc:
            raise AgentServiceError("Agent service timed out") from exc
        except httpx.HTTPStatusError as exc:
            raise AgentServiceError(
                f"Agent service returned {exc.response.status_code}: {exc.response.text}"
            ) from exc
        except Exception as exc:
            raise AgentServiceError(f"Agent service unavailable: {exc}") from exc

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url, timeout=5
            ) as client:
                r = await client.get("/health")
                return r.status_code == 200
        except Exception:
            return False


# Singleton
_agent_client: AgentClient | None = None


def get_agent_client() -> AgentClient:
    global _agent_client
    if _agent_client is None:
        _agent_client = AgentClient()
    return _agent_client

"""
Redis client — sessions, caching, rate limiting, queue.
"""

import json
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = await aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis


async def close_redis():
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

async def check_rate_limit(user_id: str, limit: int, window_seconds: int = 60) -> bool:
    """Returns True if within limit, False if exceeded."""
    r = await get_redis()
    key = f"rate:{user_id}:{window_seconds}"
    current = await r.incr(key)
    if current == 1:
        await r.expire(key, window_seconds)
    return current <= limit


# ---------------------------------------------------------------------------
# Monthly usage counter
# ---------------------------------------------------------------------------

async def increment_monthly_usage(user_id: str) -> int:
    """Increments and returns current month's usage count."""
    from datetime import datetime
    month_key = datetime.utcnow().strftime("%Y-%m")
    r = await get_redis()
    key = f"usage:{user_id}:{month_key}"
    count = await r.incr(key)
    if count == 1:
        # expire at end of next month (rough TTL 35 days)
        await r.expire(key, 35 * 86400)
    return count


async def get_monthly_usage(user_id: str) -> int:
    from datetime import datetime
    month_key = datetime.utcnow().strftime("%Y-%m")
    r = await get_redis()
    key = f"usage:{user_id}:{month_key}"
    val = await r.get(key)
    return int(val) if val else 0


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

async def cache_set(key: str, value: Any, ttl: int = settings.REDIS_CACHE_TTL):
    r = await get_redis()
    await r.set(key, json.dumps(value), ex=ttl)


async def cache_get(key: str) -> Any | None:
    r = await get_redis()
    raw = await r.get(key)
    return json.loads(raw) if raw else None


async def cache_delete(key: str):
    r = await get_redis()
    await r.delete(key)

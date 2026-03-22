"""
Shared test configuration.
"""

import asyncio
import os

import pytest

# Use test database
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://avantika:avantika@localhost:5432/avantika_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")  # DB 1 for tests
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("AGENT_SERVICE_URL", "http://localhost:8001")
os.environ.setdefault("AGENT_SERVICE_INTERNAL_KEY", "test-internal-key")
os.environ.setdefault("ENV", "development")


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

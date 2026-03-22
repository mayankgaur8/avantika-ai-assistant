"""
Language API route tests.
Mocks the AgentClient to avoid real LLM calls in CI.
"""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.services.agent_client import AgentClient


MOCK_TRANSLATION_RESULT = {
    "success": True,
    "data": {
        "primary_translation": "Guten Tag",
        "literal_translation": "Good day",
        "pronunciation": "Goo-ten Tahg",
        "alternatives": ["Hallo", "Grüß Gott"],
        "vocabulary": [{"word": "Guten", "meaning": "Good", "part_of_speech": "adjective"}],
        "cultural_note": None,
        "usage_warning": None,
        "confidence_score": 0.98,
    },
    "model_used": "gpt-4o-mini",
    "_latency_ms": 1500,
}


@pytest.fixture
def auth_headers():
    """Returns auth headers for test user. In real tests, create user first."""
    # In integration tests this would be a real JWT from test DB
    return {"Authorization": "Bearer test-token"}


@pytest.mark.asyncio
async def test_translate_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/api/v1/language/translate", json={
            "input_text": "Hello",
            "source_language": "English",
            "target_language": "German",
        })
        assert res.status_code == 401


@pytest.mark.asyncio
async def test_translate_with_mock_agent():
    with patch.object(AgentClient, "run", new=AsyncMock(return_value=MOCK_TRANSLATION_RESULT)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Register + login first
            await client.post("/api/v1/auth/register", json={
                "email": "langtest@example.com",
                "name": "Lang Test",
                "password": "password123",
            })
            login = await client.post("/api/v1/auth/login", json={
                "email": "langtest@example.com",
                "password": "password123",
            })
            token = login.json()["access_token"]

            res = await client.post(
                "/api/v1/language/translate",
                json={
                    "input_text": "Hello",
                    "source_language": "English",
                    "target_language": "German",
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            assert res.status_code == 200
            data = res.json()
            assert data["success"] is True
            assert data["data"]["primary_translation"] == "Guten Tag"

"""
Backend auth endpoint tests.
Uses pytest-asyncio + httpx AsyncClient.
"""

import pytest
from httpx import AsyncClient, ASGITransport

from backend.app.main import app


@pytest.mark.asyncio
async def test_register_and_login():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Register
        res = await client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "name": "Test User",
            "password": "password123",
        })
        assert res.status_code == 201
        data = res.json()
        assert "access_token" in data
        assert data["user"]["email"] == "test@example.com"

        # Login
        res2 = await client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "password123",
        })
        assert res2.status_code == 200
        assert "access_token" in res2.json()


@pytest.mark.asyncio
async def test_login_wrong_password():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "wrongpassword",
        })
        assert res.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/auth/me")
        assert res.status_code == 401

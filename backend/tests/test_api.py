"""Smoke tests for the API."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.mark.asyncio
async def test_healthz():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/healthz")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] in ("ok", "degraded")
        assert "version" in body
        assert "sources" in body


@pytest.mark.asyncio
async def test_meta():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/meta")
        assert r.status_code == 200
        body = r.json()
        assert "status" in body
        assert "counts" in body

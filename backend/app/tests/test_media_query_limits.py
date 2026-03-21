from httpx import AsyncClient

import pytest


@pytest.mark.anyio
async def test_upload_history_rejects_non_positive_limit(test_app):
    app, _, _, _ = test_app

    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get("/api/v1/media/history", params={"limit": 0})

    assert resp.status_code == 422


@pytest.mark.anyio
async def test_upload_history_rejects_too_large_limit(test_app):
    app, _, _, _ = test_app

    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get("/api/v1/media/history", params={"limit": 201})

    assert resp.status_code == 422


@pytest.mark.anyio
async def test_recent_media_rejects_non_positive_limit(test_app):
    app, _, _, _ = test_app

    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get("/api/v1/media/recent", params={"limit": -1})

    assert resp.status_code == 422


@pytest.mark.anyio
async def test_recent_media_rejects_too_large_limit(test_app):
    app, _, _, _ = test_app

    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get("/api/v1/media/recent", params={"limit": 500})

    assert resp.status_code == 422

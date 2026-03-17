from datetime import datetime
from pathlib import Path

import pytest
from httpx import AsyncClient

from app.api.routes import ai as ai_routes
from app.api.routes import media as media_routes
from app.models.ai import AIDetection, AIDetectionObject
from app.models.enums import AIDetectionStatus
from app.models.user import User, Workspace


async def _seed_workspace(session, user_id: int = 1, workspace_id: int = 1) -> None:
    user = User(id=user_id, email="demo@local", hashed_password="noop")
    workspace = Workspace(id=workspace_id, name="Demo", owner_user_id=user_id)
    session.add_all([user, workspace])
    await session.commit()


def _sample_bytes() -> bytes:
    assets_dir = Path(__file__).parent / "assets"
    return (assets_dir / "sample.jpg").read_bytes()


async def _fake_analyze_media(media_id: int, db, hint_item_ids=None):
    detection = AIDetection(
        media_id=media_id,
        status=AIDetectionStatus.DONE,
        raw={"objects": []},
        completed_at=datetime.utcnow(),
    )
    db.add(detection)
    await db.flush()
    db.add(
        AIDetectionObject(
            detection_id=detection.id,
            label="object",
            confidence=0.9,
            bbox={"x1": 0, "y1": 0, "x2": 10, "y2": 10},
        )
    )
    await db.commit()
    await db.refresh(detection)
    return detection


async def _fake_analyze_media_with_hints(media_id: int, db, hint_item_ids=None):
    assert hint_item_ids == [1, 2]
    return await _fake_analyze_media(media_id, db)


@pytest.mark.anyio
async def test_upload_and_history_smoke(test_app):
    app, session_factory, _, _ = test_app
    async with session_factory() as session:
        await _seed_workspace(session)

    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/media/upload",
            files={"file": ("sample.jpg", _sample_bytes(), "image/jpeg")},
            data={
                "workspace_id": "1",
                "owner_user_id": "1",
                "media_type": "photo",
                "scope": "public",
                "subdir": "smoke",
                "analyze": "false",
            },
        )
        assert resp.status_code == 200

        history = await client.get("/api/v1/media/history", params={"limit": 1, "owner_user_id": 1})
        assert history.status_code == 200
        rows = history.json()
        assert len(rows) == 1
        assert rows[0]["status"] == "success"
        assert rows[0]["file_url"]


@pytest.mark.anyio
async def test_upload_history_filters_by_location(test_app):
    app, session_factory, _, _ = test_app
    async with session_factory() as session:
        await _seed_workspace(session)

    async with AsyncClient(app=app, base_url="http://test") as client:
        loc = await client.post(
            "/api/v1/locations",
            json={"name": "Box", "workspace_id": 1},
        )
        assert loc.status_code == 201
        loc_id = loc.json()["id"]

        resp = await client.post(
            "/api/v1/media/upload",
            files={"file": ("sample.jpg", _sample_bytes(), "image/jpeg")},
            data={
                "workspace_id": "1",
                "owner_user_id": "1",
                "media_type": "photo",
                "scope": "public",
                "subdir": "smoke",
                "location_id": str(loc_id),
                "analyze": "false",
            },
        )
        assert resp.status_code == 200

        history = await client.get(
            "/api/v1/media/history",
            params={"limit": 5, "location_id": loc_id},
        )
        assert history.status_code == 200
        rows = history.json()
        assert rows
        assert all(row["location_id"] == loc_id for row in rows)


@pytest.mark.anyio
async def test_upload_with_ai_stub_updates_history(test_app, monkeypatch):
    app, session_factory, _, _ = test_app
    async with session_factory() as session:
        await _seed_workspace(session)

    monkeypatch.setattr(media_routes, "analyze_media", _fake_analyze_media)

    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/media/upload",
            files={"file": ("sample.jpg", _sample_bytes(), "image/jpeg")},
            data={
                "workspace_id": "1",
                "owner_user_id": "1",
                "media_type": "photo",
                "scope": "public",
                "subdir": "smoke",
            },
        )
        assert resp.status_code == 200

        history = await client.get("/api/v1/media/history", params={"limit": 1, "owner_user_id": 1})
        assert history.status_code == 200
        rows = history.json()
        assert rows[0]["ai_status"] == "done"
        assert rows[0]["objects"]


@pytest.mark.anyio
async def test_upload_passes_hint_item_ids(test_app, monkeypatch):
    app, session_factory, _, _ = test_app
    async with session_factory() as session:
        await _seed_workspace(session)

    monkeypatch.setattr(media_routes, "analyze_media", _fake_analyze_media_with_hints)

    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/media/upload",
            files={"file": ("sample.jpg", _sample_bytes(), "image/jpeg")},
            data={
                "workspace_id": "1",
                "owner_user_id": "1",
                "media_type": "photo",
                "scope": "public",
                "subdir": "smoke",
                "hint_item_ids": "1,2",
            },
        )
        assert resp.status_code == 200


@pytest.mark.anyio
async def test_e2e_smoke_upload_analyze_review_log(test_app, monkeypatch):
    app, session_factory, _, _ = test_app
    async with session_factory() as session:
        await _seed_workspace(session)

    monkeypatch.setattr(media_routes, "analyze_media", _fake_analyze_media)
    monkeypatch.setattr(ai_routes, "analyze_media", _fake_analyze_media)

    async with AsyncClient(app=app, base_url="http://test") as client:
        loc = await client.post(
            "/api/v1/locations",
            json={"name": "Shelf", "workspace_id": 1},
        )
        assert loc.status_code == 201
        loc_id = loc.json()["id"]

        upload = await client.post(
            "/api/v1/media/upload",
            files={"file": ("sample.jpg", _sample_bytes(), "image/jpeg")},
            data={
                "workspace_id": "1",
                "owner_user_id": "1",
                "media_type": "photo",
                "scope": "public",
                "subdir": "smoke",
                "analyze": "false",
            },
        )
        assert upload.status_code == 200
        media_id = upload.json()["id"]

        set_photo = await client.post(f"/api/v1/locations/{loc_id}/photo/{media_id}")
        assert set_photo.status_code == 201

        analyze = await client.post("/api/v1/ai/analyze", json={"media_id": media_id})
        assert analyze.status_code == 200
        detection_id = analyze.json()["id"]

        detections = await client.get("/api/v1/ai/detections", params={"status": "done"})
        assert detections.status_code == 200
        assert any(row["id"] == detection_id for row in detections.json())

        review = await client.post(
            f"/api/v1/ai/detections/{detection_id}/review_log",
            json={"action": "link_existing", "payload": {"item_id": 1}},
        )
        assert review.status_code == 200

from httpx import AsyncClient

import pytest

from app.models.ai import AIDetection, AIDetectionObject
from app.models.enums import AIDetectionDecision, AIDetectionStatus, MediaType, UploadStatus
from app.models.item import Item
from app.models.location import Location
from app.models.media import Media, MediaUploadHistory
from app.models.user import User, Workspace


async def _seed_detection_graph(session) -> int:
    user = User(id=1, email="demo@local", hashed_password="noop")
    workspace = Workspace(id=1, name="Demo", owner_user_id=1)
    item = Item(id=1, workspace_id=1, owner_user_id=1, title="Backpack")
    location = Location(id=1, workspace_id=1, name="Shelf")
    media = Media(
        id=1,
        workspace_id=1,
        owner_user_id=1,
        media_type=MediaType.PHOTO,
        path="media/demo.jpg",
    )
    detection = AIDetection(id=1, media_id=1, status=AIDetectionStatus.PENDING, raw={"objects": []})
    obj = AIDetectionObject(
        id=1,
        detection_id=1,
        label="backpack",
        confidence=0.95,
        bbox={"x1": 0, "y1": 0, "x2": 10, "y2": 10},
        decision=AIDetectionDecision.ACCEPTED,
        linked_item_id=1,
        linked_location_id=1,
    )
    history = MediaUploadHistory(
        id=1,
        media_id=1,
        workspace_id=1,
        owner_user_id=1,
        media_type=MediaType.PHOTO,
        status=UploadStatus.SUCCESS,
        ai_status=AIDetectionStatus.PENDING.value,
        path="media/demo.jpg",
    )
    session.add_all([user, workspace, item, location, media, detection, obj, history])
    await session.commit()
    return obj.id


@pytest.mark.anyio
async def test_patch_object_can_clear_links_with_explicit_null(test_app):
    app, session_factory, _, _ = test_app
    async with session_factory() as session:
        object_id = await _seed_detection_graph(session)

    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.patch(
            f"/api/v1/ai/objects/{object_id}",
            json={"item_id": None, "location_id": None},
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["linked_item_id"] is None
    assert payload["linked_location_id"] is None

    async with session_factory() as session:
        obj = await session.get(AIDetectionObject, object_id)
        history = await session.get(MediaUploadHistory, 1)
        assert obj is not None
        assert obj.linked_item_id is None
        assert obj.linked_location_id is None
        assert obj.decided_at is not None
        assert history is not None
        assert history.ai_summary["objects"][0]["linked_item_id"] is None
        assert history.ai_summary["objects"][0]["linked_location_id"] is None


@pytest.mark.anyio
async def test_patch_object_keeps_links_when_fields_are_omitted(test_app):
    app, session_factory, _, _ = test_app
    async with session_factory() as session:
        object_id = await _seed_detection_graph(session)

    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.patch(
            f"/api/v1/ai/objects/{object_id}",
            json={"decision": AIDetectionDecision.REJECTED.value},
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["decision"] == AIDetectionDecision.REJECTED.value
    assert payload["linked_item_id"] == 1
    assert payload["linked_location_id"] == 1

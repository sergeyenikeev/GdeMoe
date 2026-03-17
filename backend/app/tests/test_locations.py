from pathlib import Path

import pytest
from httpx import AsyncClient

from app.models.user import User, Workspace


async def _seed_workspace(session, user_id: int = 1, workspace_id: int = 1) -> None:
    user = User(id=user_id, email="demo@local", hashed_password="noop")
    workspace = Workspace(id=workspace_id, name="Demo", owner_user_id=user_id)
    session.add_all([user, workspace])
    await session.commit()


def _sample_bytes() -> bytes:
    assets_dir = Path(__file__).parent / "assets"
    return (assets_dir / "sample.jpg").read_bytes()


@pytest.mark.anyio
async def test_location_parent_optional_and_update_path(test_app):
    app, session_factory, _, _ = test_app
    async with session_factory() as session:
        await _seed_workspace(session)

    async with AsyncClient(app=app, base_url="http://test") as client:
        root = await client.post(
            "/api/v1/locations",
            json={"name": "Home", "workspace_id": 1, "parent_id": None},
        )
        assert root.status_code == 201
        root_id = root.json()["id"]

        child = await client.post(
            "/api/v1/locations",
            json={"name": "Room", "workspace_id": 1, "parent_id": root_id},
        )
        assert child.status_code == 201
        child_id = child.json()["id"]

        update = await client.patch(
            f"/api/v1/locations/{root_id}",
            json={"name": "Home2"},
        )
        assert update.status_code == 200

        locations = await client.get("/api/v1/locations")
        assert locations.status_code == 200
        locs = {row["id"]: row for row in locations.json()}
        assert locs[root_id]["name"] == "Home2"
        assert locs[child_id]["path"].startswith(locs[root_id]["path"])

        new_parent = await client.post(
            "/api/v1/locations",
            json={"name": "Garage", "workspace_id": 1},
        )
        assert new_parent.status_code == 201
        new_parent_id = new_parent.json()["id"]

        change_parent = await client.patch(
            f"/api/v1/locations/{child_id}",
            json={"parent_id": new_parent_id},
        )
        assert change_parent.status_code == 200

        cleared = await client.delete(f"/api/v1/locations/{child_id}/parent")
        assert cleared.status_code == 204

        refreshed = await client.get("/api/v1/locations")
        locs = {row["id"]: row for row in refreshed.json()}
        assert locs[child_id]["parent_id"] is None
        assert locs[child_id]["path"] == locs[child_id]["name"]


@pytest.mark.anyio
async def test_location_photo_linking(test_app):
    app, session_factory, _, _ = test_app
    async with session_factory() as session:
        await _seed_workspace(session)

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
                "subdir": "loc",
                "analyze": "false",
            },
        )
        assert upload.status_code == 200
        media_id = upload.json()["id"]

        link_media = await client.post(f"/api/v1/locations/{loc_id}/media/{media_id}")
        assert link_media.status_code == 201

        media_list = await client.get(f"/api/v1/locations/{loc_id}/media")
        assert media_list.status_code == 200
        assert any(row["id"] == media_id for row in media_list.json())

        link = await client.post(f"/api/v1/locations/{loc_id}/photo/{media_id}")
        assert link.status_code == 201

        locations = await client.get("/api/v1/locations")
        locs = {row["id"]: row for row in locations.json()}
        assert locs[loc_id]["photo_media_id"] == media_id

        clear = await client.delete(f"/api/v1/locations/{loc_id}/photo")
        assert clear.status_code == 204

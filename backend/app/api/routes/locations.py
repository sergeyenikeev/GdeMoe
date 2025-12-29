import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.location import Location
from app.models.item import Item
from app.models.media import Media
from app.models.enums import MediaType
from app.schemas.location import LocationCreate, LocationOut, LocationUpdate
from app.schemas.item import ItemOut
from app.api.routes.items import _serialize_item

router = APIRouter(prefix="/locations", tags=["locations"])
logger = logging.getLogger(__name__)


def _build_location_path(parent: Location | None, name: str) -> str:
    if not parent:
        return name
    base = parent.path or str(parent.id)
    return f"{base}.{name}"


async def _load_parent(db: AsyncSession, parent_id: int | None, current_id: int | None) -> Location | None:
    if parent_id is None:
        return None
    parent = await db.get(Location, parent_id)
    if not parent:
        raise HTTPException(status_code=400, detail="Parent not found")
    if current_id and parent_id == current_id:
        raise HTTPException(status_code=400, detail="Parent cannot be self")
    # Prevent cycles by walking ancestors
    cursor = parent
    while cursor and cursor.parent_id:
        if current_id and cursor.parent_id == current_id:
            raise HTTPException(status_code=400, detail="Parent creates cycle")
        cursor = await db.get(Location, cursor.parent_id)
    return parent


async def _update_descendant_paths(
    db: AsyncSession, old_path: str | None, new_path: str | None
) -> None:
    if not old_path or not new_path or old_path == new_path:
        return
    pattern = f"{old_path}.%"
    descendants = (await db.execute(select(Location).where(Location.path.like(pattern)))).scalars().all()
    for child in descendants:
        child.path = new_path + child.path[len(old_path):]


async def _validate_photo_media(db: AsyncSession, media_id: int) -> Media:
    media = await db.get(Media, media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    if media.media_type != MediaType.PHOTO:
        raise HTTPException(status_code=400, detail="Location photo must be a photo media")
    return media


def _serialize_location_media(media: Media) -> dict:
    return {
        "id": media.id,
        "path": media.path,
        "mime_type": media.mime_type,
        "media_type": media.media_type,
        "file_url": f"/api/v1/media/file/{media.id}",
        "thumb_url": f"/api/v1/media/file/{media.id}?thumb=1" if media.thumb_path else None,
    }

@router.get("", response_model=list[LocationOut])
@router.get("/", response_model=list[LocationOut])
async def list_locations(db: AsyncSession = Depends(get_db)) -> list[Location]:
    res = await db.execute(select(Location).order_by(Location.parent_id.nullsfirst(), Location.id))
    return res.scalars().all()


@router.post("", response_model=LocationOut, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=LocationOut, status_code=status.HTTP_201_CREATED)
async def create_location(payload: LocationCreate, db: AsyncSession = Depends(get_db)) -> Location:
    if not payload.name or not payload.name.strip():
        raise HTTPException(status_code=400, detail="Location name is required")
    parent = await _load_parent(db, payload.parent_id, None)
    photo_media: Media | None = None
    if payload.photo_media_id:
        photo_media = await _validate_photo_media(db, payload.photo_media_id)
        if photo_media.workspace_id != payload.workspace_id:
            raise HTTPException(status_code=400, detail="Media workspace mismatch")
    location = Location(**payload.dict(exclude={"photo_media_id"}))
    location.path = _build_location_path(parent, payload.name)
    db.add(location)
    await db.commit()
    await db.refresh(location)
    if photo_media:
        photo_media.location_id = location.id
        location.photo_media_id = photo_media.id
        await db.commit()
        await db.refresh(location)
    logger.info(
        "location.create id=%s parent_id=%s photo_media_id=%s",
        location.id,
        payload.parent_id,
        payload.photo_media_id,
    )
    return location


@router.patch("/{location_id}", response_model=LocationOut)
async def update_location(location_id: int, payload: LocationUpdate, db: AsyncSession = Depends(get_db)) -> Location:
    loc = await db.get(Location, location_id)
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    data = payload.dict(exclude_unset=True)
    if "name" in data and (data["name"] is None or not data["name"].strip()):
        raise HTTPException(status_code=400, detail="Location name is required")
    if "photo_media_id" in data and data["photo_media_id"] is not None:
        media = await _validate_photo_media(db, data["photo_media_id"])
        if media.workspace_id != loc.workspace_id:
            raise HTTPException(status_code=400, detail="Media workspace mismatch")
        media.location_id = loc.id
        loc.photo_media_id = media.id
    if "photo_media_id" in data and data["photo_media_id"] is None:
        loc.photo_media_id = None
    parent_id = data.get("parent_id", loc.parent_id)
    name = data.get("name", loc.name)
    if "parent_id" in data or "name" in data:
        parent = await _load_parent(db, parent_id, loc.id)
        new_path = _build_location_path(parent, name)
        old_path = loc.path
        loc.path = new_path
        await _update_descendant_paths(db, old_path, new_path)
    for k, v in data.items():
        if k in {"photo_media_id", "parent_id", "name"}:
            continue
        setattr(loc, k, v)
    if "parent_id" in data:
        loc.parent_id = parent_id
    if "name" in data:
        loc.name = name
    await db.commit()
    await db.refresh(loc)
    logger.info(
        "location.update id=%s parent_id=%s photo_media_id=%s",
        loc.id,
        loc.parent_id,
        loc.photo_media_id,
    )
    return loc


@router.delete("/{location_id}/parent", status_code=status.HTTP_204_NO_CONTENT)
async def clear_location_parent(location_id: int, db: AsyncSession = Depends(get_db)):
    loc = await db.get(Location, location_id)
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    old_path = loc.path
    loc.parent_id = None
    loc.path = _build_location_path(None, loc.name)
    await _update_descendant_paths(db, old_path, loc.path)
    await db.commit()
    logger.info("location.parent.clear id=%s", location_id)
    return None


@router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_location(location_id: int, db: AsyncSession = Depends(get_db)):
    loc = await db.get(Location, location_id)
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    await db.delete(loc)
    await db.commit()
    return None


@router.get("/{location_id}/items", response_model=list[ItemOut])
async def items_for_location(location_id: int, db: AsyncSession = Depends(get_db)) -> list[ItemOut]:
    stmt = select(Item).where(Item.location_id == location_id).order_by(Item.created_at.desc())
    items = (await db.execute(stmt)).scalars().all()
    return [await _serialize_item(item, db) for item in items]


@router.get("/{location_id}/media")
async def list_location_media(location_id: int, db: AsyncSession = Depends(get_db)) -> list[dict]:
    location = await db.get(Location, location_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    media_rows = (
        await db.execute(select(Media).where(Media.location_id == location_id).order_by(Media.id.desc()))
    ).scalars().all()
    return [_serialize_location_media(media) for media in media_rows]


@router.post("/{location_id}/media/{media_id}", status_code=status.HTTP_201_CREATED)
async def link_media_to_location(location_id: int, media_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    location = await db.get(Location, location_id)
    media = await db.get(Media, media_id)
    if not location or not media:
        raise HTTPException(status_code=404, detail="Location or media not found")
    if media.workspace_id != location.workspace_id:
        raise HTTPException(status_code=400, detail="Media workspace mismatch")
    media.location_id = location_id
    await db.commit()
    logger.info("location.media.link location_id=%s media_id=%s", location_id, media_id)
    return {"location_id": location_id, "media_id": media_id}


@router.post("/{location_id}/photo/{media_id}", status_code=status.HTTP_201_CREATED)
async def set_location_photo(location_id: int, media_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    location = await db.get(Location, location_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    media = await _validate_photo_media(db, media_id)
    if media.workspace_id != location.workspace_id:
        raise HTTPException(status_code=400, detail="Media workspace mismatch")
    media.location_id = location_id
    location.photo_media_id = media_id
    await db.commit()
    logger.info("location.photo.set location_id=%s media_id=%s", location_id, media_id)
    return {"location_id": location_id, "photo_media_id": media_id}


@router.delete("/{location_id}/photo", status_code=status.HTTP_204_NO_CONTENT)
async def clear_location_photo(location_id: int, db: AsyncSession = Depends(get_db)):
    location = await db.get(Location, location_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    location.photo_media_id = None
    await db.commit()
    logger.info("location.photo.clear location_id=%s", location_id)
    return None

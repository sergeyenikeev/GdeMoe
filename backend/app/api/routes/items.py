import os
import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.models.item import Item
from app.models.media import Media, ItemMedia
from app.models.ai import AIDetection, AIDetectionObject
from app.models.tag import Tag, ItemTag
from app.schemas.item import ItemCreate, ItemOut, ItemUpdate
from app.models.user import User
from app.models.enums import ItemStatus

router = APIRouter(prefix="/items", tags=["items"])


async def _item_tags(item_id: int, db: AsyncSession) -> list[str]:
    stmt = (
        select(Tag.name)
        .join(ItemTag, ItemTag.tag_id == Tag.id)
        .where(ItemTag.item_id == item_id)
    )
    rows = await db.execute(stmt)
    return [r[0] for r in rows.all()]


async def _serialize_item(item: Item, db: AsyncSession) -> ItemOut:
    tags = await _item_tags(item.id, db)
    attrs: dict = item.attributes or {}
    # normalize links to list[str]
    links_val = attrs.get("links")
    links_list: list[str] | None = None
    if isinstance(links_val, list):
        links_list = [str(x) for x in links_val]
    elif isinstance(links_val, str):
        try:
            parsed = json.loads(links_val)
            if isinstance(parsed, list):
                links_list = [str(x) for x in parsed]
            else:
                links_list = [links_val]
        except Exception:
            links_list = [links_val]
    attrs["links"] = links_list or []
    return ItemOut(
        id=item.id,
        workspace_id=item.workspace_id,
        owner_user_id=item.owner_user_id,
        title=item.title,
        description=item.description,
        category=item.category,
        status=item.status,
        attributes=item.attributes,
        links=attrs.get("links"),
        purchase_datetime=attrs.get("purchase_datetime"),
        quantity=attrs.get("quantity"),
        manufacturer=attrs.get("manufacturer"),
        origin_country=attrs.get("origin_country"),
        location_ids=attrs.get("location_ids"),
        model=item.model,
        serial_number=item.serial_number,
        purchase_date=item.purchase_date,
        price=float(item.price) if item.price is not None else None,
        currency=item.currency,
        store=item.store,
        order_number=item.order_number,
        order_url=item.order_url,
        warranty_until=item.warranty_until,
        expiration_date=item.expiration_date,
        reminders=item.reminders,
        location_id=item.location_id,
        scope=item.scope,
        created_at=item.created_at,
        updated_at=item.updated_at,
        tags=tags,
    )


@router.get("/", response_model=list[ItemOut])
async def list_items(db: AsyncSession = Depends(get_db)) -> list[ItemOut]:
    result = await db.execute(select(Item).order_by(Item.created_at.desc()).limit(100))
    items = result.scalars().all()
    return [await _serialize_item(item, db) for item in items]


@router.get("/search", response_model=list[ItemOut])
async def search_items(
    query: str = "",
    status: ItemStatus | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[ItemOut]:
    stmt = select(Item).order_by(Item.created_at.desc()).limit(100)
    if query:
        pattern = f"%{query.lower()}%"
        stmt = stmt.where(
            (Item.title.ilike(pattern))
            | (Item.description.ilike(pattern))
            | (Item.category.ilike(pattern))
        )
    if status:
        stmt = stmt.where(Item.status == status)
    rows = await db.execute(stmt)
    items = rows.scalars().all()
    return [await _serialize_item(item, db) for item in items]


@router.post("/", response_model=ItemOut, status_code=status.HTTP_201_CREATED)
async def create_item(
    payload: ItemCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ItemOut:
    data = payload.dict(exclude_none=True)
    # ensure status is valid enum
    status = data.get("status", ItemStatus.OK)
    if isinstance(status, str):
        try:
            data["status"] = ItemStatus(status)
        except Exception:
            data["status"] = ItemStatus.OK
    tags = data.pop("tags", [])
    attrs = data.get("attributes") or {}
    links = data.pop("links", None)
    for attr_key in ["purchase_datetime", "quantity", "manufacturer", "origin_country", "location_ids"]:
        val = data.pop(attr_key, None)
        if val is not None:
            attrs[attr_key] = val
    if links is not None:
        attrs["links"] = list(links)
    if attrs:
        data["attributes"] = attrs
    data.setdefault("workspace_id", 2)
    item = Item(**data, owner_user_id=user.id)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    await _upsert_tags(item.id, item.workspace_id, tags, db)
    await db.commit()
    await db.refresh(item)
    return await _serialize_item(item, db)


@router.get("/{item_id}", response_model=ItemOut)
async def get_item(item_id: int, db: AsyncSession = Depends(get_db)) -> Item:
    item = await db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return await _serialize_item(item, db)


@router.patch("/{item_id}", response_model=ItemOut)
async def update_item(
    item_id: int,
    payload: ItemUpdate,
    db: AsyncSession = Depends(get_db),
) -> ItemOut:
    item = await db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    data = payload.dict(exclude_unset=True)
    tags = data.pop("tags", None)
    existing_attrs: dict = item.attributes or {}
    attrs = data.get("attributes") or {}
    # merge existing attributes to avoid losing saved keys
    attrs = {**existing_attrs, **attrs}
    # move known attributes into attrs to persist JSON
    links = data.pop("links", None)
    for attr_key in ["purchase_datetime", "quantity", "manufacturer", "origin_country", "location_ids"]:
        val = data.pop(attr_key, None)
        if val is not None:
            attrs[attr_key] = val
    if links is not None:
        attrs["links"] = list(links)
    if attrs:
        data["attributes"] = attrs
    for k, v in data.items():
        setattr(item, k, v)
    await db.commit()
    if tags is not None:
        await _upsert_tags(item.id, item.workspace_id, tags, db)
        await db.commit()
    await db.refresh(item)
    return await _serialize_item(item, db)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
):
    item = await db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    await db.delete(item)
    await db.commit()
    return None


def _serialize_media(media: Media, detection: AIDetection | None, objects: list[AIDetectionObject]) -> dict:
    return {
        "id": media.id,
        "path": media.path,
        "mime_type": media.mime_type,
        "file_url": f"/api/v1/media/file/{media.id}",
        "detection": {
            "id": detection.id if detection else None,
            "status": detection.status if detection else None,
            "objects": [
                {
                    "label": obj.label,
                    "confidence": float(obj.confidence),
                    "bbox": obj.bbox,
                    "suggested_location_id": obj.suggested_location_id,
                    "decision": obj.decision,
                    "linked_item_id": obj.linked_item_id,
                    "linked_location_id": obj.linked_location_id,
                }
                for obj in objects
            ],
        }
        if detection
        else None,
    }


@router.get("/{item_id}/media")
async def list_item_media(item_id: int, db: AsyncSession = Depends(get_db)):
    item = await db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    stmt = (
        select(Media)
        .join(ItemMedia, ItemMedia.media_id == Media.id)
        .where(ItemMedia.item_id == item_id)
        .order_by(Media.id.desc())
    )
    media_rows = (await db.execute(stmt)).scalars().all()
    result = []
    for media in media_rows:
        det_stmt = (
            select(AIDetection)
            .where(AIDetection.media_id == media.id)
            .order_by(AIDetection.id.desc())
            .limit(1)
        )
        det = (await db.execute(det_stmt)).scalar_one_or_none()
        obj_stmt = select(AIDetectionObject).where(
            AIDetectionObject.detection_id == (det.id if det else -1)
        )
        objects = (await db.execute(obj_stmt)).scalars().all() if det else []
        result.append(_serialize_media(media, det, list(objects)))
    return result


@router.post("/{item_id}/media/{media_id}", status_code=status.HTTP_201_CREATED)
async def link_media_to_item(item_id: int, media_id: int, db: AsyncSession = Depends(get_db)):
    item = await db.get(Item, item_id)
    media = await db.get(Media, media_id)
    if not item or not media:
        raise HTTPException(status_code=404, detail="Item or media not found")
    exists_stmt = select(ItemMedia).where(ItemMedia.item_id == item_id, ItemMedia.media_id == media_id)
    exists = (await db.execute(exists_stmt)).scalar_one_or_none()
    if not exists:
        db.add(ItemMedia(item_id=item_id, media_id=media_id))
        await db.commit()
    return {"item_id": item_id, "media_id": media_id}


@router.delete("/{item_id}/media/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_media_from_item(
    item_id: int,
    media_id: int,
    delete_file: bool = False,
    db: AsyncSession = Depends(get_db),
):
    link_stmt = select(ItemMedia).where(ItemMedia.item_id == item_id, ItemMedia.media_id == media_id)
    link = (await db.execute(link_stmt)).scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    await db.delete(link)
    if delete_file:
        media = await db.get(Media, media_id)
        if media:
            await db.delete(media)
            # delete physical file best-effort
            scope = "private" if media.path.startswith("private/") else "public"
            base = Path(settings.media_private_path if scope == "private" else settings.media_public_path)
            rel = Path(media.path.removeprefix("private/")) if scope == "private" else Path(media.path)
            full_path = base / rel
            try:
                if full_path.exists():
                    full_path.unlink()
            except Exception:
                pass
            # cleanup detections
            await db.execute(delete(AIDetection).where(AIDetection.media_id == media_id))
    await db.commit()
    return None


async def _upsert_tags(item_id: int, workspace_id: int, tags: list[str], db: AsyncSession):
    # remove existing
    await db.execute(delete(ItemTag).where(ItemTag.item_id == item_id))
    if not tags:
        return
    names = [t.strip() for t in tags if t.strip()]
    if not names:
        return
    existing_stmt = select(Tag).where(Tag.name.in_(names), Tag.workspace_id == workspace_id)
    existing = {t.name: t for t in (await db.execute(existing_stmt)).scalars().all()}
    for name in names:
        tag = existing.get(name)
        if not tag:
            tag = Tag(workspace_id=workspace_id, name=name)
            db.add(tag)
            await db.flush()
        db.add(ItemTag(item_id=item_id, tag_id=tag.id))

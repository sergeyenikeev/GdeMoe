import asyncio
import os
from datetime import datetime
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import settings
from app.models.media import Media
from app.models.ai import AIDetection, AIDetectionObject, AIDetectionStatus
from app.models.enums import MediaType
from app.services.ai.pipeline import analyze_media
from app.services.ai.video import analyze_video
from app.db.session import AsyncSessionLocal

router = APIRouter(prefix="/media", tags=["media"])


def _ensure_extension(filename: str, mime: str | None, media_type: str) -> str:
    name = os.path.basename(filename)
    if "." in name:
        return name
    if mime and "jpeg" in mime:
        return name + ".jpg"
    if mime and "png" in mime:
        return name + ".png"
    if mime and "heic" in mime:
        return name + ".heic"
    if media_type == "video":
        return name + ".mp4"
    return name + ".bin"


@router.post("/upload")
async def upload_media(
    file: UploadFile = File(...),
    workspace_id: int = Form(2),
    owner_user_id: int = Form(1),
    media_type: str = Form("photo"),
    mime_type: str | None = Form(None),
    subdir: str = Form("uploads"),
    scope: str = Form("public"),  # public | private
    db: AsyncSession = Depends(get_db),
):
    try:
        media_type_enum = MediaType(media_type)
    except Exception:
        raise HTTPException(status_code=400, detail="Unsupported media_type; allowed: photo, video, document")

    base = Path(settings.media_public_path if scope == "public" else settings.media_private_path)
    target_dir = base / subdir / datetime.utcnow().strftime("%Y%m%d")
    target_dir.mkdir(parents=True, exist_ok=True)

    filename = file.filename or f"upload_{int(datetime.utcnow().timestamp())}"
    filename = _ensure_extension(filename, mime_type or file.content_type, media_type)
    target_path = target_dir / filename

    async with aiofiles.open(target_path, "wb") as out:
        while chunk := await file.read(1024 * 1024):
            await out.write(chunk)

    rel_path = target_path.relative_to(base)
    rel_path_str = str(rel_path)
    if scope == "private":
        rel_path_str = f"private/{rel_path_str}"
    media = Media(
        workspace_id=workspace_id,
        owner_user_id=owner_user_id,
        media_type=media_type_enum,
        path=rel_path_str,
        mime_type=mime_type or file.content_type,
    )
    db.add(media)
    await db.commit()
    await db.refresh(media)

    # Синхронно анализируем, чтобы не зависать в "pending"
    try:
        if media_type == "video":
            await analyze_video(media.id, db)
        else:
            await analyze_media(media.id, db)
    except Exception as exc:  # noqa: BLE001
        det = AIDetection(media_id=media.id, status=AIDetectionStatus.FAILED, raw={"error": str(exc)})
        db.add(det)
        await db.commit()

    return {"id": media.id, "path": media.path, "mime_type": media.mime_type}


@router.get("/recent")
async def recent_media(scope: str = "public", limit: int = 20, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Media)
        .order_by(Media.id.desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()
    result = []
    for m in rows:
        if scope == "public" and m.path.startswith("private/"):
            continue
        if scope == "private" and not m.path.startswith("private/"):
            continue
        # detections
        det_stmt = (
            select(AIDetection)
            .where(AIDetection.media_id == m.id)
            .order_by(AIDetection.id.desc())
            .limit(1)
        )
        det = (await db.execute(det_stmt)).scalar_one_or_none()
        objects = []
        if det:
            obj_stmt = select(AIDetectionObject).where(AIDetectionObject.detection_id == det.id)
            objects = (await db.execute(obj_stmt)).scalars().all()
        result.append(
            {
                "id": m.id,
                "path": m.path,
                "mime_type": m.mime_type,
                "file_url": f"/api/v1/media/file/{m.id}",
                "detection": {
                    "id": det.id if det else None,
                    "status": det.status if det else None,
                    "objects": [
                        {
                            "label": o.label,
                            "confidence": float(o.confidence),
                            "bbox": o.bbox,
                        }
                        for o in objects
                    ],
                }
                if det
                else None,
            }
        )
    return result


@router.get("/file/{media_id}")
async def get_media_file(media_id: int, db: AsyncSession = Depends(get_db)):
    media = await db.get(Media, media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    scope = "private" if media.path.startswith("private/") else "public"
    base = Path(settings.media_private_path if scope == "private" else settings.media_public_path)
    rel = Path(media.path.removeprefix("private/")) if scope == "private" else Path(media.path)
    full_path = base / rel
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    return FileResponse(full_path, media_type=media.mime_type, filename=full_path.name)

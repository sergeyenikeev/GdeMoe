import hashlib
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Iterable, Literal

import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db
from app.core.config import settings
from app.models.ai import AIDetection, AIDetectionObject, AIDetectionStatus
from app.models.enums import MediaType, UploadStatus
from app.models.media import ItemMedia, Media, MediaUploadHistory
from app.schemas.media import MediaUploadHistoryOut
from app.services.ai.pipeline import analyze_media
from app.services.ai.video import analyze_video

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/media", tags=["media"])

SANITIZE_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _sanitize_segment(segment: str, fallback: str) -> str:
    cleaned = SANITIZE_RE.sub("_", segment.strip())
    cleaned = cleaned.lstrip(".").strip("_")
    return cleaned or fallback


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


async def _write_file(target_path: Path, file: UploadFile, max_bytes: int) -> tuple[int, str]:
    sha = hashlib.sha256()
    total = 0
    async with aiofiles.open(target_path, "wb") as out:
        while chunk := await file.read(1024 * 1024):
            total += len(chunk)
            if total > max_bytes:
                await out.close()
                target_path.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="File is too large")
            sha.update(chunk)
            await out.write(chunk)
    return total, sha.hexdigest()


def _make_image_thumb(src: Path, dest: Path) -> None:
    from PIL import Image

    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as img:
        img.thumbnail((512, 512))
        img.save(dest, format="JPEG")


def _make_video_thumb(src: Path, dest: Path) -> None:
    try:
        import cv2  # noqa: WPS433
    except ImportError:
        logger.warning("cv2 not available; skip video thumb for %s", src)
        return
    cap = cv2.VideoCapture(str(src))
    ok, frame = cap.read()
    cap.release()
    if not ok or frame is None:
        logger.warning("Cannot read first frame for thumb %s", src)
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(dest), frame)


async def _latest_detection(db: AsyncSession, media_id: int) -> tuple[AIDetection | None, list[AIDetectionObject]]:
    det_stmt = (
        select(AIDetection)
        .where(AIDetection.media_id == media_id)
        .order_by(AIDetection.id.desc())
        .limit(1)
    )
    det = (await db.execute(det_stmt)).scalar_one_or_none()
    objects: list[AIDetectionObject] = []
    if det:
        obj_stmt = (
            select(AIDetectionObject)
            .options(selectinload(AIDetectionObject.candidates))
            .where(AIDetectionObject.detection_id == det.id)
        )
        objects = (await db.execute(obj_stmt)).scalars().all()
    return det, list(objects)


def _serialize_detection(det: AIDetection | None, objects: Iterable[AIDetectionObject]) -> dict | None:
    if not det:
        return None
    return {
        "id": det.id,
        "status": det.status,
        "objects": [
            _serialize_detection_object(obj)
            for obj in objects
        ],
    }


def _serialize_media(m: Media, det: AIDetection | None, objects: Iterable[AIDetectionObject]) -> dict:
    scope_prefix = "private/" if m.path.startswith("private/") else ""
    return {
        "id": m.id,
        "path": m.path,
        "mime_type": m.mime_type,
        "size_bytes": m.size_bytes,
        "file_hash": m.file_hash,
        "thumb_path": m.thumb_path,
        "file_url": f"/api/v1/media/file/{m.id}",
        "thumb_url": f"/api/v1/media/file/{m.id}?thumb=1" if m.thumb_path else None,
        "analysis": _serialize_detection(det, objects),
    }


def _serialize_detection_object(obj: AIDetectionObject) -> dict:
    return {
        "id": obj.id,
        "label": obj.label,
        "confidence": float(obj.confidence),
        "bbox": obj.bbox,
        "suggested_location_id": obj.suggested_location_id,
        "decision": obj.decision,
        "linked_item_id": obj.linked_item_id,
        "linked_location_id": obj.linked_location_id,
        "candidates": [
            {"item_id": c.item_id, "score": float(c.score)}
            for c in getattr(obj, "candidates", [])
        ],
    }


async def _create_upload_log(
    db: AsyncSession,
    workspace_id: int,
    owner_user_id: int,
    media_type: MediaType,
    source: str | None,
) -> MediaUploadHistory:
    entry = MediaUploadHistory(
        workspace_id=workspace_id,
        owner_user_id=owner_user_id,
        media_type=media_type,
        status=UploadStatus.IN_PROGRESS,
        source=source or "upload",
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def _mark_upload_failed(db: AsyncSession, entry: MediaUploadHistory | None, error: str) -> None:
    if entry is None:
        return
    try:
        await db.rollback()
    except Exception:
        pass
    entry.status = UploadStatus.FAILED
    entry.ai_status = "failed"
    entry.ai_summary = {"error": error}
    db.add(entry)
    await db.commit()


def _validate_mime(mime: str | None, media_type: MediaType) -> str:
    mime_lower = (mime or "").lower()
    if mime_lower and mime_lower not in [m.lower() for m in settings.media_allowed_mimes]:
        raise HTTPException(status_code=400, detail=f"Unsupported mime type: {mime_lower}")
    if media_type == MediaType.PHOTO and mime_lower and not mime_lower.startswith("image/"):
        raise HTTPException(status_code=400, detail="media_type=photo conflicts with mime_type")
    if media_type == MediaType.VIDEO and mime_lower and not mime_lower.startswith("video/"):
        raise HTTPException(status_code=400, detail="media_type=video conflicts with mime_type")
    return mime_lower


@router.post("/upload")
async def upload_media(
    file: UploadFile = File(...),
    workspace_id: int = Form(2),
    owner_user_id: int = Form(1),
    media_type: str = Form("photo"),
    mime_type: str | None = Form(None),
    subdir: str = Form("inbox"),
    scope: Literal["public", "private"] = Form("public"),
    item_id: int | None = Form(None),
    location_id: int | None = Form(None),
    analyze: bool = Form(True),
    source: str | None = Form("upload"),
    client_created_at: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    try:
        media_type_enum = MediaType(media_type)
    except Exception:
        raise HTTPException(status_code=400, detail="Unsupported media_type; allowed: photo, video, document")
    upload_log: MediaUploadHistory | None = None
    try:
        upload_log = await _create_upload_log(db, workspace_id, owner_user_id, media_type_enum, source)
        mime_lower = _validate_mime(mime_type or file.content_type, media_type_enum)
        base = Path(settings.media_public_path if scope == "public" else settings.media_private_path)
        safe_workspace = _sanitize_segment(str(workspace_id), "workspace")
        safe_owner = _sanitize_segment(str(owner_user_id), "user")
        target_group = _sanitize_segment(subdir, "inbox") if not item_id else f"item_{item_id}"
        target_dir = base / safe_workspace / safe_owner / target_group / datetime.utcnow().strftime("%Y%m%d")
        target_dir.mkdir(parents=True, exist_ok=True)

        filename = file.filename or f"upload_{int(datetime.utcnow().timestamp())}"
        filename = _ensure_extension(filename, mime_lower or file.content_type, media_type)
        filename = _sanitize_segment(filename, f"upload.{media_type_enum.value}")
        target_path = target_dir / filename

        max_bytes = settings.media_max_photo_size_bytes if media_type_enum == MediaType.PHOTO else settings.media_max_video_size_bytes
        try:
            size_bytes, file_hash = await _write_file(target_path, file, max_bytes=max_bytes)
        finally:
            await file.close()

        rel_path = target_path.relative_to(base)
        rel_path_str = f"private/{rel_path}" if scope == "private" else str(rel_path)

        thumb_rel_path: str | None = None
        if media_type_enum in (MediaType.PHOTO, MediaType.VIDEO):
            thumb_dir = base / "thumbs" / safe_workspace / safe_owner / target_group / target_dir.name
            thumb_name = f"{target_path.stem}.jpg"
            thumb_path = thumb_dir / thumb_name
            try:
                if media_type_enum == MediaType.PHOTO:
                    _make_image_thumb(target_path, thumb_path)
                else:
                    _make_video_thumb(target_path, thumb_path)
                if thumb_path.exists():
                    thumb_rel_path = thumb_path.relative_to(base)
                    thumb_rel_path = f"private/{thumb_rel_path}" if scope == "private" else str(thumb_rel_path)
                upload_log.thumb_path = thumb_rel_path
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to build thumbnail for %s: %s", target_path, exc)

        media = Media(
            workspace_id=workspace_id,
            owner_user_id=owner_user_id,
            location_id=location_id,
            media_type=media_type_enum,
            path=rel_path_str,
            mime_type=mime_type or file.content_type,
            size_bytes=size_bytes,
            file_hash=file_hash,
            thumb_path=thumb_rel_path,
        )
        db.add(media)
        await db.commit()
        await db.refresh(media)

        if item_id:
            existing = await db.execute(
                select(ItemMedia).where(ItemMedia.item_id == item_id, ItemMedia.media_id == media.id)
            )
            if not existing.scalar_one_or_none():
                db.add(ItemMedia(item_id=item_id, media_id=media.id))
                await db.commit()

        analysis_status: dict | None = None
        if analyze:
            try:
                if media_type_enum == MediaType.VIDEO:
                    detection_ids = await analyze_video(
                        media.id,
                        db,
                        frame_stride=settings.video_frame_stride,
                        max_frames=settings.video_max_frames,
                    )
                    latest = None
                    if detection_ids:
                        latest = await db.get(AIDetection, detection_ids[-1])
                    analysis_status = {
                        "detection_ids": detection_ids,
                        "status": latest.status if latest else "done" if detection_ids else "pending",
                    }
                else:
                    det = await analyze_media(media.id, db)
                    analysis_status = {"detection_id": det.id, "status": det.status}
            except Exception as exc:  # noqa: BLE001
                logger.exception("Analyze failed for media %s: %s", media.id, exc)
                db.add(AIDetection(media_id=media.id, status=AIDetectionStatus.FAILED, raw={"error": str(exc)}))
                await db.commit()
                analysis_status = {"status": "failed"}

        det, objects = await _latest_detection(db, media.id)
        upload_log.media_id = media.id
        upload_log.path = media.path
        upload_log.thumb_path = media.thumb_path or upload_log.thumb_path
        upload_log.status = UploadStatus.SUCCESS
        ai_status_value = (analysis_status or {}).get("status") or (det.status if det else None)
        if hasattr(ai_status_value, "value"):
            ai_status_value = ai_status_value.value
        upload_log.ai_status = ai_status_value
        upload_log.ai_summary = _serialize_detection(det, objects)
        upload_log.detection_id = det.id if det else None
        db.add(upload_log)
        await db.commit()

        logger.info(
            "media_upload",
            extra={
                "media_id": media.id,
                "source": source or "upload",
                "size_bytes": size_bytes,
                "mime": mime_type or file.content_type,
            },
        )

        return {
            "id": media.id,
            "path": media.path,
            "mime_type": media.mime_type,
            "size_bytes": media.size_bytes,
            "file_hash": media.file_hash,
            "thumb_path": media.thumb_path,
            "analysis": analysis_status,
        }
    except HTTPException as exc:
        await _mark_upload_failed(db, upload_log, str(exc.detail if hasattr(exc, "detail") else exc))
        raise
    except Exception as exc:  # noqa: BLE001
        await _mark_upload_failed(db, upload_log, str(exc))
        raise


@router.get("/{media_id}")
async def get_media(media_id: int, db: AsyncSession = Depends(get_db)):
    media = await db.get(Media, media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    det, objects = await _latest_detection(db, media_id)
    return _serialize_media(media, det, objects)


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
        det, objects = await _latest_detection(db, m.id)
        result.append(_serialize_media(m, det, objects))
    return result


@router.get("/history", response_model=list[MediaUploadHistoryOut])
async def upload_history(
    owner_user_id: int | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    logger.info("media.history.list owner=%s limit=%s", owner_user_id, limit)
    stmt = select(MediaUploadHistory).order_by(MediaUploadHistory.created_at.desc()).limit(limit)
    if owner_user_id:
        stmt = stmt.where(MediaUploadHistory.owner_user_id == owner_user_id)
    rows = (await db.execute(stmt)).scalars().all()
    result: list[MediaUploadHistoryOut] = []
    for entry in rows:
        det: AIDetection | None = None
        objects: list[AIDetectionObject] = []
        if entry.media_id:
            det, objects = await _latest_detection(db, entry.media_id)
        file_url = f"/api/v1/media/file/{entry.media_id}" if entry.media_id else None
        thumb_url = (
            f"/api/v1/media/file/{entry.media_id}?thumb=1"
            if entry.media_id and (entry.thumb_path or (det and det.media and det.media.thumb_path))
            else None
        )
        result.append(
            MediaUploadHistoryOut(
                id=entry.id,
                media_id=entry.media_id,
                workspace_id=entry.workspace_id,
                owner_user_id=entry.owner_user_id,
                media_type=entry.media_type,
                status=entry.status,
                source=entry.source,
                ai_status=entry.ai_status,
                ai_summary=entry.ai_summary,
                path=entry.path,
                thumb_path=entry.thumb_path,
                file_url=file_url,
                thumb_url=thumb_url,
                detection_id=entry.detection_id or (det.id if det else None),
                objects=[_serialize_detection_object(obj) for obj in objects],
                created_at=entry.created_at,
            )
        )
    return result


@router.get("/file/{media_id}")
async def get_media_file(
    media_id: int,
    thumb: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    media = await db.get(Media, media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    path_field = media.thumb_path if thumb else media.path
    scope = "private" if path_field and path_field.startswith("private/") else "public"
    base = Path(settings.media_private_path if scope == "private" else settings.media_public_path)
    rel_path = path_field or media.path
    rel = Path(rel_path.removeprefix("private/")) if scope == "private" else Path(rel_path)
    full_path = base / rel
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    media_type = "image/jpeg" if thumb else media.mime_type
    return FileResponse(full_path, media_type=media_type, filename=full_path.name)

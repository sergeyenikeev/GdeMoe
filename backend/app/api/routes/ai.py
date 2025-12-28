import httpx
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.api.deps import get_db
from app.core.config import settings
from app.models.ai import AIDetection, AIDetectionObject, AIDetectionReview
from app.models.item import Item
from app.models.location import Location
from app.models.media import Media
from app.models.media import MediaUploadHistory
from app.models.enums import (
    AIDetectionDecision,
    AIDetectionReviewAction,
    AIDetectionStatus as AIDetectionStatusEnum,
)
from app.schemas.ai import (
    AIDetectionActionRequest,
    AIDetectionOut,
    AIDetectionObjectOut,
    AIDetectionReviewRequest,
    AITaskRequest,
    AIDetectionObjectUpdate,
)
from app.services.ai.pipeline import analyze_media
from app.services.ai.video import analyze_video

router = APIRouter(prefix="/ai", tags=["ai"])
logger = logging.getLogger(__name__)


async def _ensure_exists(db: AsyncSession, model, obj_id: int | None, label: str) -> None:
    if obj_id is None:
        return
    stmt = select(model.id).where(model.id == obj_id)
    exists = (await db.execute(stmt)).scalar_one_or_none()
    if exists is None:
        raise HTTPException(status_code=404, detail=f"{label} not found")


async def _resolve_review_user_id(db: AsyncSession, detection: AIDetection) -> int | None:
    result = await db.execute(select(Media.owner_user_id).where(Media.id == detection.media_id))
    return result.scalar_one_or_none()


@router.post("/analyze")
async def request_analysis(payload: AITaskRequest, db: AsyncSession = Depends(get_db)):
    # If external AI service configured, enqueue there
    if settings.ai_service_url:
        detection = AIDetection(media_id=payload.media_id, status=AIDetectionStatusEnum.PENDING)
        db.add(detection)
        await db.commit()
        await db.refresh(detection)
        await _update_upload_history(db, detection)
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                await client.post(
                    f"{settings.ai_service_url}/tasks",
                    json={"media_id": payload.media_id, "callback_id": detection.id},
                )
            except Exception as exc:  # noqa: BLE001
                raise HTTPException(status_code=502, detail=f"AI service unavailable: {exc}") from exc
        loaded = await _load_detection(db, detection.id)
        return loaded

    logger.info("ai.analyze.start media_id=%s", payload.media_id)
    # Local pipeline (YOLO + CLIP)
    try:
        detection = await analyze_media(payload.media_id, db)
    except ImportError as exc:
        logger.exception("ai.analyze.failed media_id=%s", payload.media_id)
        raise HTTPException(
            status_code=503,
            detail=f"AI dependencies missing on backend: {exc}. Install torch/ultralytics/open_clip.",
        ) from exc

    await _update_upload_history(db, detection)
    # Reload with objects eager-loaded to avoid async lazy-load issues
    return await _load_detection(db, detection.id)


@router.post("/analyze_video")
async def request_video_analysis(payload: AITaskRequest, db: AsyncSession = Depends(get_db)):
    # Samples frames and runs image pipeline
    detection_ids = await analyze_video(payload.media_id, db)
    if detection_ids:
        latest = await db.get(AIDetection, detection_ids[-1])
        if latest:
            await _update_upload_history(db, latest)
    return {"media_id": payload.media_id, "detections": detection_ids}


@router.get("/detections", response_model=list[AIDetectionOut])
async def list_detections(
    status: AIDetectionStatusEnum = AIDetectionStatusEnum.PENDING,
    db: AsyncSession = Depends(get_db),
):
    logger.info("ai.detections.list status=%s", status)
    result = await db.execute(
        select(AIDetection)
        .where(AIDetection.status == status)
        .options(
            selectinload(AIDetection.media),
            selectinload(AIDetection.objects).selectinload(AIDetectionObject.candidates),
        )
    )
    detections = result.scalars().unique().all()
    out: list[AIDetectionOut] = []
    for det in detections:
        out.append(
            AIDetectionOut(
                id=det.id,
                media_id=det.media_id,
                status=det.status,
                created_at=det.created_at,
                completed_at=det.completed_at,
                media_path=det.media.path if det.media else None,
                thumb_path=det.media.thumb_path if det.media else None,
                objects=[_object_out(obj) for obj in det.objects],
            )
        )
    return out


@router.post("/detections/{detection_id}/accept", response_model=AIDetectionOut)
async def accept_detection(
    detection_id: int, body: AIDetectionActionRequest, db: AsyncSession = Depends(get_db)
):
    logger.info("ai.detection.accept id=%s item_id=%s location_id=%s", detection_id, body.item_id, body.location_id)
    detection = await db.get(AIDetection, detection_id)
    if detection is None:
        raise HTTPException(status_code=404, detail="Detection not found")
    await _ensure_exists(db, Item, body.item_id, "Item")
    await _ensure_exists(db, Location, body.location_id, "Location")
    review_user_id = await _resolve_review_user_id(db, detection)
    detection.status = AIDetectionStatusEnum.DONE
    detection.completed_at = datetime.utcnow()
    values: dict = {"decision": AIDetectionDecision.ACCEPTED, "decided_at": datetime.utcnow()}
    if body.item_id is not None:
        values["linked_item_id"] = body.item_id
    if body.location_id is not None:
        values["linked_location_id"] = body.location_id
    await db.execute(
        update(AIDetectionObject)
        .where(AIDetectionObject.detection_id == detection_id)
        .values(**values)
    )
    db.add(
        AIDetectionReview(
            detection_id=detection_id,
            user_id=review_user_id,
            action=AIDetectionReviewAction.ACCEPT,
            payload=body.model_dump(),
        )
    )
    await db.commit()
    await db.refresh(detection)
    await _update_upload_history(db, detection)
    return await _load_detection(db, detection_id)


@router.post("/detections/{detection_id}/reject", response_model=AIDetectionOut)
async def reject_detection(
    detection_id: int, body: AIDetectionActionRequest | None = None, db: AsyncSession = Depends(get_db)
):
    logger.info("ai.detection.reject id=%s item_id=%s location_id=%s", detection_id, body.item_id if body else None, body.location_id if body else None)
    detection = await db.get(AIDetection, detection_id)
    if detection is None:
        raise HTTPException(status_code=404, detail="Detection not found")
    if body:
        await _ensure_exists(db, Item, body.item_id, "Item")
        await _ensure_exists(db, Location, body.location_id, "Location")
    review_user_id = await _resolve_review_user_id(db, detection)
    detection.status = AIDetectionStatusEnum.FAILED
    detection.completed_at = datetime.utcnow()
    values: dict = {"decision": AIDetectionDecision.REJECTED, "decided_at": datetime.utcnow()}
    if body and body.item_id is not None:
        values["linked_item_id"] = body.item_id
    if body and body.location_id is not None:
        values["linked_location_id"] = body.location_id
    await db.execute(
        update(AIDetectionObject)
        .where(AIDetectionObject.detection_id == detection_id)
        .values(**values)
    )
    db.add(
        AIDetectionReview(
            detection_id=detection_id,
            user_id=review_user_id,
            action=AIDetectionReviewAction.REJECT,
            payload=body.model_dump() if body else {},
        )
    )
    await db.commit()
    await db.refresh(detection)
    await _update_upload_history(db, detection)
    return await _load_detection(db, detection_id)


@router.post("/detections/{detection_id}/review_log")
async def add_review_log(
    detection_id: int, body: AIDetectionReviewRequest, db: AsyncSession = Depends(get_db)
):
    logger.info("ai.detection.review_log id=%s action=%s", detection_id, body.action)
    detection = await db.get(AIDetection, detection_id)
    if detection is None:
        raise HTTPException(status_code=404, detail="Detection not found")
    review_user_id = await _resolve_review_user_id(db, detection)
    db.add(
        AIDetectionReview(
            detection_id=detection_id,
            user_id=review_user_id,
            action=body.action,
            payload=body.payload,
        )
    )
    await db.commit()
    return {"status": "ok"}


@router.patch("/objects/{object_id}", response_model=AIDetectionObjectOut)
async def update_detection_object(
    object_id: int,
    body: AIDetectionObjectUpdate,
    db: AsyncSession = Depends(get_db),
):
    logger.info(
        "ai.detection.object.update id=%s item_id=%s location_id=%s decision=%s",
        object_id,
        body.item_id,
        body.location_id,
        body.decision,
    )
    obj = await db.get(AIDetectionObject, object_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Detection object not found")
    await _ensure_exists(db, Item, body.item_id, "Item")
    await _ensure_exists(db, Location, body.location_id, "Location")
    if body.item_id is not None:
        obj.linked_item_id = body.item_id
    if body.location_id is not None:
        obj.linked_location_id = body.location_id
    if body.decision is not None:
        obj.decision = body.decision
    obj.decided_at = datetime.utcnow()
    await db.commit()
    await db.refresh(obj)
    parent = await db.get(AIDetection, obj.detection_id)
    if parent:
        await _update_upload_history(db, parent)
    return _object_out(obj)


async def _load_detection(db: AsyncSession, detection_id: int) -> AIDetectionOut:
    result = await db.execute(
        select(AIDetection)
        .where(AIDetection.id == detection_id)
        .options(
            selectinload(AIDetection.media),
            selectinload(AIDetection.objects).selectinload(AIDetectionObject.candidates),
        )
    )
    det = result.scalar_one()
    return AIDetectionOut(
        id=det.id,
        media_id=det.media_id,
        status=det.status,
        created_at=det.created_at,
        completed_at=det.completed_at,
        media_path=det.media.path if det.media else None,
        thumb_path=det.media.thumb_path if det.media else None,
        objects=[_object_out(obj) for obj in det.objects],
    )


def _object_out(obj: AIDetectionObject) -> AIDetectionObjectOut:
    return AIDetectionObjectOut(
        id=obj.id,
        label=obj.label,
        confidence=float(obj.confidence),
        bbox=obj.bbox,
        suggested_location_id=obj.suggested_location_id,
        decision=obj.decision,
        linked_item_id=obj.linked_item_id,
        linked_location_id=obj.linked_location_id,
        candidates=[{"item_id": c.item_id, "score": float(c.score)} for c in obj.candidates],
    )


async def _update_upload_history(db: AsyncSession, detection: AIDetection) -> None:
    loaded = await db.execute(
        select(AIDetection)
        .where(AIDetection.id == detection.id)
        .options(selectinload(AIDetection.objects))
    )
    det = loaded.scalar_one_or_none()
    if det is None:
        return
    result = await db.execute(
        select(MediaUploadHistory)
        .where(MediaUploadHistory.media_id == det.media_id)
        .order_by(MediaUploadHistory.created_at.desc())
        .limit(1)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        return
    entry.ai_status = det.status.value if hasattr(det.status, "value") else str(det.status)
    entry.ai_summary = {
        "detection_id": det.id,
        "objects": [
            {
                "id": obj.id,
                "label": obj.label,
                "confidence": float(obj.confidence),
                "linked_item_id": obj.linked_item_id,
                "linked_location_id": obj.linked_location_id,
                "decision": obj.decision,
            }
            for obj in det.objects
        ],
    }
    entry.detection_id = det.id
    await db.commit()

import httpx
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.api.deps import get_db
from app.core.config import settings
from app.models.ai import AIDetection, AIDetectionObject, AIDetectionReview
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
)
from app.services.ai.pipeline import analyze_media
from app.services.ai.video import analyze_video

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/analyze")
async def request_analysis(payload: AITaskRequest, db: AsyncSession = Depends(get_db)):
    # If external AI service configured, enqueue there
    if settings.ai_service_url:
        detection = AIDetection(media_id=payload.media_id, status=AIDetectionStatus.PENDING)
        db.add(detection)
        await db.commit()
        await db.refresh(detection)
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                await client.post(
                    f"{settings.ai_service_url}/tasks",
                    json={"media_id": payload.media_id, "callback_id": detection.id},
                )
            except Exception as exc:  # noqa: BLE001
                raise HTTPException(status_code=502, detail=f"AI service unavailable: {exc}") from exc
        return {
            "id": detection.id,
            "media_id": detection.media_id,
            "status": detection.status,
            "created_at": detection.created_at,
            "completed_at": detection.completed_at,
            "objects": [],
        }

    # Local pipeline (YOLO + CLIP)
    try:
        detection = await analyze_media(payload.media_id, db)
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"AI dependencies missing on backend: {exc}. Install torch/ultralytics/open_clip.",
        ) from exc

    # Reload with objects eager-loaded to avoid async lazy-load issues
    result = await db.execute(
        select(AIDetection).options(selectinload(AIDetection.objects)).where(AIDetection.id == detection.id)
    )
    detection_with_objects = result.scalar_one()
    objects_out = [
        AIDetectionObjectOut(
            label=obj.label,
            confidence=float(obj.confidence),
            bbox=obj.bbox,
            candidates=[],
        )
        for obj in detection_with_objects.objects
    ]
    return {
        "id": detection_with_objects.id,
        "media_id": detection_with_objects.media_id,
        "status": detection_with_objects.status,
        "created_at": detection_with_objects.created_at,
        "completed_at": detection_with_objects.completed_at,
        "objects": [obj.model_dump() for obj in objects_out],
    }


@router.post("/analyze_video")
async def request_video_analysis(payload: AITaskRequest, db: AsyncSession = Depends(get_db)):
    # Samples frames and runs image pipeline
    detection_ids = await analyze_video(payload.media_id, db)
    return {"media_id": payload.media_id, "detections": detection_ids}


@router.get("/detections", response_model=list[AIDetectionOut])
async def list_detections(
    status: AIDetectionStatusEnum = AIDetectionStatusEnum.PENDING,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AIDetection)
        .where(AIDetection.status == status)
        .options(selectinload(AIDetection.objects).selectinload(AIDetectionObject.candidates))
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
                objects=[
                    AIDetectionObjectOut(
                        id=obj.id,
                        label=obj.label,
                        confidence=float(obj.confidence),
                        bbox=obj.bbox,
                        suggested_location_id=obj.suggested_location_id,
                        decision=obj.decision,
                        candidates=[
                            {"item_id": c.item_id, "score": float(c.score)} for c in obj.candidates
                        ],
                    )
                    for obj in det.objects
                ],
            )
        )
    return out


@router.post("/detections/{detection_id}/accept", response_model=AIDetectionOut)
async def accept_detection(
    detection_id: int, body: AIDetectionActionRequest, db: AsyncSession = Depends(get_db)
):
    detection = await db.get(AIDetection, detection_id)
    if detection is None:
        raise HTTPException(status_code=404, detail="Detection not found")
    detection.status = AIDetectionStatusEnum.DONE
    detection.completed_at = datetime.utcnow()
    await db.execute(
        update(AIDetectionObject)
        .where(AIDetectionObject.detection_id == detection_id)
        .values(decision=AIDetectionDecision.ACCEPTED, decided_at=datetime.utcnow())
    )
    db.add(
        AIDetectionReview(
            detection_id=detection_id,
            action=AIDetectionReviewAction.ACCEPT,
            payload=body.model_dump(),
        )
    )
    await db.commit()
    await db.refresh(detection)
    return await _load_detection(db, detection_id)


@router.post("/detections/{detection_id}/reject", response_model=AIDetectionOut)
async def reject_detection(
    detection_id: int, body: AIDetectionActionRequest | None = None, db: AsyncSession = Depends(get_db)
):
    detection = await db.get(AIDetection, detection_id)
    if detection is None:
        raise HTTPException(status_code=404, detail="Detection not found")
    detection.status = AIDetectionStatusEnum.FAILED
    detection.completed_at = datetime.utcnow()
    await db.execute(
        update(AIDetectionObject)
        .where(AIDetectionObject.detection_id == detection_id)
        .values(decision=AIDetectionDecision.REJECTED, decided_at=datetime.utcnow())
    )
    db.add(
        AIDetectionReview(
            detection_id=detection_id,
            action=AIDetectionReviewAction.REJECT,
            payload=body.model_dump() if body else {},
        )
    )
    await db.commit()
    await db.refresh(detection)
    return await _load_detection(db, detection_id)


@router.post("/detections/{detection_id}/review_log")
async def add_review_log(
    detection_id: int, body: AIDetectionReviewRequest, db: AsyncSession = Depends(get_db)
):
    detection = await db.get(AIDetection, detection_id)
    if detection is None:
        raise HTTPException(status_code=404, detail="Detection not found")
    db.add(
        AIDetectionReview(
            detection_id=detection_id,
            action=body.action,
            payload=body.payload,
        )
    )
    await db.commit()
    return {"status": "ok"}


async def _load_detection(db: AsyncSession, detection_id: int) -> AIDetectionOut:
    result = await db.execute(
        select(AIDetection)
        .where(AIDetection.id == detection_id)
        .options(selectinload(AIDetection.objects).selectinload(AIDetectionObject.candidates))
    )
    det = result.scalar_one()
    return AIDetectionOut(
        id=det.id,
        media_id=det.media_id,
        status=det.status,
        created_at=det.created_at,
        completed_at=det.completed_at,
        objects=[
            AIDetectionObjectOut(
                id=obj.id,
                label=obj.label,
                confidence=float(obj.confidence),
                bbox=obj.bbox,
                suggested_location_id=obj.suggested_location_id,
                decision=obj.decision,
                candidates=[{"item_id": c.item_id, "score": float(c.score)} for c in obj.candidates],
            )
            for obj in det.objects
        ],
    )

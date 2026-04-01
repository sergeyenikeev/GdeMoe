"""Маршруты для AI-review и запуска анализа.

Сами вычисления живут в `app.services.ai.*`, а этот слой отвечает за HTTP-
контракт, обновление статусов и синхронизацию с журналом загрузок.
"""

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
    """Проверяет существование связанных сущностей до записи решения review.

    Выполняет запрос к базе данных для проверки, существует ли объект
    с указанным ID. Используется перед принятием решений по review,
    чтобы избежать ссылок на несуществующие предметы или локации.

    Args:
        db: Асинхронная сессия базы данных.
        model: ORM-модель для проверки (Item, Location и т.д.).
        obj_id: ID объекта для проверки (может быть None).
        label: Название сущности для сообщения об ошибке.

    Raises:
        HTTPException: Если объект не найден.
    """
    if obj_id is None:
        return
    stmt = select(model.id).where(model.id == obj_id)
    exists = (await db.execute(stmt)).scalar_one_or_none()
    if exists is None:
        raise HTTPException(status_code=404, detail=f"{label} not found")


async def _detection_workspace_id(db: AsyncSession, detection: AIDetection) -> int | None:
    """Return workspace of the media attached to detection."""
    result = await db.execute(select(Media.workspace_id).where(Media.id == detection.media_id))
    return result.scalar_one_or_none()


async def _ensure_same_workspace(
    db: AsyncSession,
    model,
    obj_id: int | None,
    label: str,
    workspace_id: int | None,
) -> None:
    """Prevent cross-workspace links during AI review operations."""
    if obj_id is None or workspace_id is None:
        return
    stmt = select(model.workspace_id).where(model.id == obj_id)
    obj_workspace_id = (await db.execute(stmt)).scalar_one_or_none()
    if obj_workspace_id is None:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    if obj_workspace_id != workspace_id:
        raise HTTPException(status_code=400, detail=f"{label} belongs to another workspace")


async def _resolve_review_user_id(db: AsyncSession, detection: AIDetection) -> int | None:
    """Берёт владельца медиа как пользователя, принявшего решение по review.

    Определяет пользователя, который загрузил медиа-файл, связанный с детекцией.
    Этот пользователь считается ответственным за review-действия.

    Args:
        db: Асинхронная сессия базы данных.
        detection: Объект детекции AI.

    Returns:
        ID пользователя-владельца медиа или None.
    """
    result = await db.execute(select(Media.owner_user_id).where(Media.id == detection.media_id))
    return result.scalar_one_or_none()


def _field_was_provided(body: AIDetectionObjectUpdate, field_name: str) -> bool:
    """Differentiate omitted PATCH fields from explicit nulls."""
    return field_name in body.model_fields_set


@router.post("/analyze")
async def request_analysis(payload: AITaskRequest, db: AsyncSession = Depends(get_db)):
    """Запускает анализ изображения локально или через внешний AI-сервис.

    В зависимости от настроек (ai_service_url) либо отправляет задачу
    на внешний сервис, либо выполняет анализ локально с помощью
    Ultralytics и OpenCLIP. Создаёт запись детекции и обновляет историю загрузок.

    Args:
        payload: Данные запроса анализа (media_id, hint_item_ids).
        db: Асинхронная сессия базы данных.

    Returns:
        Объект AIDetectionOut с результатами анализа.

    Raises:
        HTTPException: Если AI-сервис недоступен или отсутствуют зависимости.
    """
    # Если настроен внешний сервис, backend выступает как оркестратор:
    # создаёт запись детекции и отправляет задачу наружу.
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
                    json={
                        "media_id": payload.media_id,
                        "callback_id": detection.id,
                        "hint_item_ids": payload.hint_item_ids,
                    },
                )
            except Exception as exc:  # noqa: BLE001
                raise HTTPException(status_code=502, detail=f"AI service unavailable: {exc}") from exc
        loaded = await _load_detection(db, detection.id)
        return loaded

    logger.info("ai.analyze.start media_id=%s hint_items=%s", payload.media_id, payload.hint_item_ids)
    # Локальный режим нужен для автономной работы без внешнего AI-сервиса.
    try:
        detection = await analyze_media(payload.media_id, db, hint_item_ids=payload.hint_item_ids)
    except ImportError as exc:
        logger.exception("ai.analyze.failed media_id=%s", payload.media_id)
        raise HTTPException(
            status_code=503,
            detail=f"AI dependencies missing on backend: {exc}. Install torch/ultralytics/open_clip.",
        ) from exc

    await _update_upload_history(db, detection)
    # Перечитываем запись с eager loading, чтобы не ловить async lazy-load в сериализации.
    return await _load_detection(db, detection.id)


@router.post("/analyze_video")
async def request_video_analysis(payload: AITaskRequest, db: AsyncSession = Depends(get_db)):
    """Запускает анализ видео через выборку кадров.

    Извлекает кадры из видео, анализирует каждый как изображение
    и создаёт детекции для найденных объектов. Обновляет историю загрузок
    для последнего кадра.

    Args:
        payload: Данные запроса анализа (media_id, hint_item_ids).
        db: Асинхронная сессия базы данных.

    Returns:
        Словарь с media_id и списком ID детекций.
    """
    detection_ids = await analyze_video(payload.media_id, db, hint_item_ids=payload.hint_item_ids)
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
    """Возвращает очередь AI-детекций по статусу.

    Извлекает все детекции с указанным статусом, включая связанные
    медиа и объекты детекции с кандидатами. Используется для отображения
    очереди на review.

    Args:
        status: Статус детекций для фильтрации (по умолчанию PENDING).
        db: Асинхронная сессия базы данных.

    Returns:
        Список объектов AIDetectionOut.
    """
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
    """Подтверждает детекцию и при необходимости привязывает item/location.

    Помечает детекцию как завершённую, обновляет все объекты детекции
    с решением ACCEPTED и связывает с указанными предметом/локацией.
    Записывает действие в журнал review и обновляет историю загрузок.

    Args:
        detection_id: ID детекции.
        body: Данные действия (item_id, location_id).
        db: Асинхронная сессия базы данных.

    Returns:
        Обновлённый объект AIDetectionOut.

    Raises:
        HTTPException: Если детекция или связанные сущности не найдены.
    """
    logger.info("ai.detection.accept id=%s item_id=%s location_id=%s", detection_id, body.item_id, body.location_id)
    detection = await db.get(AIDetection, detection_id)
    if detection is None:
        raise HTTPException(status_code=404, detail="Detection not found")
    workspace_id = await _detection_workspace_id(db, detection)
    await _ensure_exists(db, Item, body.item_id, "Item")
    await _ensure_exists(db, Location, body.location_id, "Location")
    await _ensure_same_workspace(db, Item, body.item_id, "Item", workspace_id)
    await _ensure_same_workspace(db, Location, body.location_id, "Location", workspace_id)
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
    """Отклоняет детекцию и сохраняет решение в журнал review.

    Помечает детекцию как FAILED, обновляет объекты с решением REJECTED
    и опционально связывает с предметом/локацией. Записывает действие
    в аудит-лог и обновляет историю загрузок.

    Args:
        detection_id: ID детекции.
        body: Опциональные данные действия (item_id, location_id).
        db: Асинхронная сессия базы данных.

    Returns:
        Обновлённый объект AIDetectionOut.

    Raises:
        HTTPException: Если детекция не найдена.
    """
    logger.info("ai.detection.reject id=%s item_id=%s location_id=%s", detection_id, body.item_id if body else None, body.location_id if body else None)
    detection = await db.get(AIDetection, detection_id)
    if detection is None:
        raise HTTPException(status_code=404, detail="Detection not found")
    workspace_id = await _detection_workspace_id(db, detection)
    if body:
        await _ensure_exists(db, Item, body.item_id, "Item")
        await _ensure_exists(db, Location, body.location_id, "Location")
        await _ensure_same_workspace(db, Item, body.item_id, "Item", workspace_id)
        await _ensure_same_workspace(db, Location, body.location_id, "Location", workspace_id)
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
    """Пишет произвольное действие review в аудит-лог.

    Позволяет записывать дополнительные действия пользователя
    по review детекции (например, комментарии или промежуточные решения)
    в таблицу AIDetectionReview для аудита.

    Args:
        detection_id: ID детекции.
        body: Данные review (action, payload).
        db: Асинхронная сессия базы данных.

    Returns:
        Словарь со статусом "ok".

    Raises:
        HTTPException: Если детекция не найдена.
    """
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
    """Позволяет точечно поправить один объект детекции без пересоздания всей записи.

    Обновляет поля объекта детекции (связи с item/location, решение)
    и обновляет время принятия решения. Синхронизирует историю загрузок.

    Args:
        object_id: ID объекта детекции.
        body: Данные для обновления (item_id, location_id, decision).
        db: Асинхронная сессия базы данных.

    Returns:
        Обновлённый объект AIDetectionObjectOut.

    Raises:
        HTTPException: Если объект не найден.
    """
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
    parent = await db.get(AIDetection, obj.detection_id)
    workspace_id = await _detection_workspace_id(db, parent) if parent else None
    changed = False
    if _field_was_provided(body, "item_id"):
        await _ensure_same_workspace(db, Item, body.item_id, "Item", workspace_id)
        obj.linked_item_id = body.item_id
        changed = True
    if _field_was_provided(body, "location_id"):
        await _ensure_same_workspace(db, Location, body.location_id, "Location", workspace_id)
        obj.linked_location_id = body.location_id
        changed = True
    if body.decision is not None:
        obj.decision = body.decision
        changed = True
    if changed:
        obj.decided_at = datetime.utcnow()
    await db.commit()
    await db.refresh(obj)
    if parent:
        await _update_upload_history(db, parent)
    return await _load_detection_object(db, object_id)


async def _load_detection(db: AsyncSession, detection_id: int) -> AIDetectionOut:
    """Загружает детекцию вместе с медиа и кандидатами для ответа API.

    Выполняет eager loading связанных объектов (media, objects, candidates)
    для избежания lazy-load проблем при сериализации.

    Args:
        db: Асинхронная сессия базы данных.
        detection_id: ID детекции.

    Returns:
        Объект AIDetectionOut с полными данными.
    """
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


async def _load_detection_object(db: AsyncSession, object_id: int) -> AIDetectionObjectOut:
    """Load one detection object with eager-loaded candidates for PATCH responses."""
    result = await db.execute(
        select(AIDetectionObject)
        .where(AIDetectionObject.id == object_id)
        .options(selectinload(AIDetectionObject.candidates))
    )
    return _object_out(result.scalar_one())


def _object_out(obj: AIDetectionObject) -> AIDetectionObjectOut:
    """Сериализует объект детекции в формат ответа API.

    Преобразует ORM-объект в Pydantic-модель для JSON-ответа,
    включая список кандидатов с их скорами.

    Args:
        obj: ORM-объект AIDetectionObject.

    Returns:
        Объект AIDetectionObjectOut.
    """
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
    """Синхронизирует `MediaUploadHistory` с актуальным состоянием AI.

    Обновляет запись истории загрузки медиа с текущим статусом AI,
    summary объектов детекции и ID детекции. Используется для отслеживания
    прогресса обработки медиа.

    Args:
        db: Асинхронная сессия базы данных.
        detection: Объект детекции AI.
    """
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

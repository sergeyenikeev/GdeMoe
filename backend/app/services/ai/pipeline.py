"""Основной пайплайн анализа изображений.

В нормальном режиме здесь происходит такая цепочка:
1. читаем сохранённый файл;
2. детектим объекты через YOLO или фолбэк;
3. считаем эмбеддинги для матчинга, если доступен CLIP;
4. создаём записи детекций и кандидатов привязки к предметам.
"""

from io import BytesIO
import logging
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.ai import AIDetection, AIDetectionCandidate, AIDetectionObject, AIDetectionStatus
from app.models.item import Item
from app.models.enums import MediaType
from app.models.media import ItemMedia, Media
from app.services.ai.detector import DetectedObject, detect_objects
from app.services.ai.embeddings import image_embedding

try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
except Exception:
    pass

logger = logging.getLogger(__name__)
CANDIDATE_TOP_K = 3
CANDIDATE_MAX_ITEMS = 200
HINT_CANDIDATE_SCORE = 0.95


def _resolve_media_path(media_path: str) -> Path:
    """Преобразует путь из БД в реальный путь на диске.

    Определяет базовую директорию (public или private) на основе префикса пути
    и возвращает полный путь к файлу.

    Args:
        media_path (str): Путь к медиа из базы данных.

    Returns:
        Path: Полный путь к файлу на диске.
    """
    rel_path = Path(media_path)
    if rel_path.is_absolute():
        return rel_path
    base = settings.media_private_path if media_path.startswith("private/") else settings.media_public_path
    if media_path.startswith("private/"):
        rel_path = Path(media_path.removeprefix("private/"))
    return Path(base) / rel_path


async def _load_item_media_embeddings(
    db: AsyncSession,
    workspace_id: int,
    location_id: int | None,
    max_items: int,
) -> list[tuple[int, np.ndarray]]:
    """Собирает эмбеддинги по последним фото предметов в workspace.

    Загружает последние фотографии предметов из указанного workspace,
    вычисляет их эмбеддинги и возвращает список пар (item_id, embedding).
    Ограничивает количество предметов для производительности.

    Args:
        db (AsyncSession): Асинхронная сессия базы данных.
        workspace_id (int): ID рабочего пространства.
        location_id (int | None): ID локации для фильтрации предметов.
        max_items (int): Максимальное количество предметов.

    Returns:
        list[tuple[int, np.ndarray]]: Список пар (item_id, embedding).
    """
    stmt = (
        select(Item.id, Media.path, Media.mime_type)
        .join(ItemMedia, ItemMedia.item_id == Item.id)
        .join(Media, Media.id == ItemMedia.media_id)
        .where(Item.workspace_id == workspace_id)
        .where(Media.media_type == MediaType.PHOTO)
        .order_by(Media.id.desc())
    )
    if location_id:
        stmt = stmt.where(Item.location_id == location_id)
    rows = (await db.execute(stmt)).all()
    embeddings: list[tuple[int, np.ndarray]] = []
    seen: set[int] = set()
    for item_id, media_path, mime_type in rows:
        if item_id in seen:
            continue
        seen.add(item_id)
        if mime_type and not mime_type.lower().startswith("image/"):
            continue
        full_path = _resolve_media_path(media_path)
        if not full_path.exists():
            continue
        try:
            with full_path.open("rb") as f:
                image = Image.open(BytesIO(f.read())).convert("RGB")
            emb = image_embedding(image)
            embeddings.append((item_id, emb))
        except Exception as exc:  # noqa: BLE001
            logger.warning("item_embedding_failed item_id=%s path=%s err=%s", item_id, full_path, exc)
        if len(embeddings) >= max_items:
            break
    return embeddings


def _top_k_candidates(
    query_embedding: np.ndarray,
    item_embeddings: Iterable[tuple[int, np.ndarray]],
    top_k: int,
) -> list[tuple[int, float]]:
    """Считает косинусную близость и оставляет лучшие совпадения.

    Вычисляет косинусное расстояние между query-эмбеддингом и эмбеддингами предметов,
    нормализует scores в диапазон [0,1] и возвращает топ-k кандидатов.

    Args:
        query_embedding (np.ndarray): Эмбеддинг запроса (объекта из изображения).
        item_embeddings (Iterable[tuple[int, np.ndarray]]): Итерируемый объект с парами (item_id, embedding).
        top_k (int): Количество лучших кандидатов для возврата.

    Returns:
        list[tuple[int, float]]: Список пар (item_id, score) отсортированный по убыванию score.
    """
    q = query_embedding.astype("float32")
    q_norm = np.linalg.norm(q) or 1.0
    q = q / q_norm
    scores: list[tuple[int, float]] = []
    for item_id, emb in item_embeddings:
        score = float(np.dot(q, emb))
        scores.append((item_id, max(0.0, min(1.0, score))))
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores[:top_k]


async def _resolve_hint_item_ids(
    db: AsyncSession,
    workspace_id: int,
    hint_item_ids: list[int] | None,
) -> list[int]:
    """Оставляет только те `hint_item_ids`, которые реально есть в workspace.

    Фильтрует список hint_item_ids, оставляя только предметы,
    принадлежащие указанному workspace.

    Args:
        db (AsyncSession): Асинхронная сессия базы данных.
        workspace_id (int): ID рабочего пространства.
        hint_item_ids (list[int] | None): Список ID предметов для проверки.

    Returns:
        list[int]: Список валидных ID предметов из hint_item_ids.
    """
    if not hint_item_ids:
        return []
    stmt = select(Item.id).where(
        Item.workspace_id == workspace_id,
        Item.id.in_(hint_item_ids),
    )
    return [row[0] for row in (await db.execute(stmt)).all()]


async def analyze_media(media_id: int, db: AsyncSession, hint_item_ids: list[int] | None = None) -> AIDetection:
    """Анализирует одно изображение и создаёт запись `AIDetection`.

    Выполняет полный пайплайн анализа: детекцию объектов через YOLO,
    вычисление эмбеддингов через CLIP, поиск кандидатов среди предметов
    по хэшу, hint'ам и схожести эмбеддингов. Создаёт объекты детекции
    и кандидатов привязки.

    Args:
        media_id (int): ID медиафайла для анализа.
        db (AsyncSession): Асинхронная сессия базы данных.
        hint_item_ids (list[int] | None): Список ID предметов для приоритизации в кандидатах.

    Returns:
        AIDetection: Созданная запись детекции с результатами анализа.

    Raises:
        ValueError: Если медиа не найдено.
        FileNotFoundError: Если файл медиа не существует на диске.
    """
    media = await db.get(Media, media_id)
    if not media:
        raise ValueError("Media not found")

    # Работаем уже с файлом, который был ранее сохранён upload-эндпоинтом.
    media_path = _resolve_media_path(media.path)
    if not media_path.exists():
        raise FileNotFoundError(f"Media file not found: {media_path}")

    valid_hint_items = await _resolve_hint_item_ids(db, media.workspace_id, hint_item_ids)
    detection_row = AIDetection(
        media_id=media_id,
        status=AIDetectionStatus.IN_PROGRESS,
        raw={"objects": [], "hint_item_ids": valid_hint_items},
    )
    db.add(detection_row)
    await db.flush()

    try:
        with media_path.open("rb") as f:
            image = Image.open(BytesIO(f.read())).convert("RGB")
        image_np = np.array(image)

        detections = detect_objects(image_np)
        # Если модель не нашла ничего, создаём единичную рамку по всему изображению.
        if not detections:
            # Даже если модель ничего не нашла, создаём общий bbox.
            # Так пользователь видит, что анализ состоялся, а не "пропал".
            w, h = image.size
            detections = [DetectedObject((0, 0, w, h), "object", 0.5)]

        hash_candidates: dict[int, float] = {}
        if media.file_hash:
            # Совпадение по хэшу — самый дешёвый сигнал для повторных загрузок.
            stmt = (
                select(Item.id)
                .join(ItemMedia, ItemMedia.item_id == Item.id)
                .join(Media, Media.id == ItemMedia.media_id)
                .where(Item.workspace_id == media.workspace_id)
                .where(Media.file_hash == media.file_hash)
                .where(Media.id != media.id)
            )
            if media.location_id:
                stmt = stmt.where(Item.location_id == media.location_id)
            for row in (await db.execute(stmt)).all():
                hash_candidates[row[0]] = 0.99

        item_embeddings: list[tuple[int, np.ndarray]] | None = None

        for det in detections:
            crop = image.crop(det.bbox)
            embedding_list: list[float] | None = None
            try:
                emb = image_embedding(crop)
                embedding_list = emb.tolist()
            except ImportError as exc:  # noqa: BLE001
                detection_row.raw.setdefault("warnings", []).append(f"clip_unavailable:{exc}")
            except Exception as exc:  # noqa: BLE001
                detection_row.raw.setdefault("warnings", []).append(f"clip_error:{exc}")
            det_obj = AIDetectionObject(
                detection_id=detection_row.id,
                label=det.label,
                confidence=det.score,
                bbox={"x1": det.bbox[0], "y1": det.bbox[1], "x2": det.bbox[2], "y2": det.bbox[3]},
                suggested_location_id=None,
            )
            detection_row.raw["objects"].append(
                {
                    "label": det.label,
                    "confidence": det.score,
                    "bbox": det_obj.bbox,
                    "embedding": embedding_list,
                }
            )
            db.add(det_obj)
            await db.flush()

            # Начинаем с хэш-кандидатов и добавляем временные подсказки.
            candidate_scores: dict[int, float] = dict(hash_candidates)
            for item_id in valid_hint_items:
                candidate_scores[item_id] = max(candidate_scores.get(item_id, 0.0), HINT_CANDIDATE_SCORE)
            if embedding_list is not None:
                if item_embeddings is None:
                    # Базу эмбеддингов подгружаем лениво, только если CLIP реально сработал.
                    try:
                        item_embeddings = await _load_item_media_embeddings(
                            db,
                            workspace_id=media.workspace_id,
                            location_id=media.location_id,
                            max_items=CANDIDATE_MAX_ITEMS,
                        )
                    except Exception as exc:  # noqa: BLE001
                        detection_row.raw.setdefault("warnings", []).append(f"clip_candidates_error:{exc}")
                        item_embeddings = []
                if item_embeddings:
                    clip_candidates = _top_k_candidates(
                        np.array(embedding_list, dtype="float32"),
                        item_embeddings,
                        CANDIDATE_TOP_K,
                    )
                    for item_id, score in clip_candidates:
                        candidate_scores[item_id] = max(candidate_scores.get(item_id, 0.0), score)

            for item_id, score in sorted(candidate_scores.items(), key=lambda x: x[1], reverse=True)[:CANDIDATE_TOP_K]:
                db.add(
                    AIDetectionCandidate(
                        detection_object_id=det_obj.id,
                        item_id=item_id,
                        score=score,
                    )
                )

        detection_row.status = AIDetectionStatus.DONE
        detection_row.completed_at = func.now()
    except Exception as exc:  # noqa: BLE001
        # Ошибку тоже сохраняем в raw, чтобы её было видно в истории и логах.
        detection_row.status = AIDetectionStatus.FAILED
        detection_row.raw = {**(detection_row.raw or {}), "error": str(exc)}
        detection_row.completed_at = func.now()

    await db.commit()
    await db.refresh(detection_row)
    return detection_row

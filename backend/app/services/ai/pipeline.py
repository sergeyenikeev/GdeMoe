"""
AI pipeline:
- загружает медиа
- детектит объекты (YOLO или фолбэк)
- считает эмбеддинги (CLIP, если доступен)
- создает записи детекций с bbox/labels
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


def _resolve_media_path(media_path: str) -> Path:
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
    q = query_embedding.astype("float32")
    q_norm = np.linalg.norm(q) or 1.0
    q = q / q_norm
    scores: list[tuple[int, float]] = []
    for item_id, emb in item_embeddings:
        score = float(np.dot(q, emb))
        scores.append((item_id, max(0.0, min(1.0, score))))
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores[:top_k]


async def analyze_media(media_id: int, db: AsyncSession) -> AIDetection:
    media = await db.get(Media, media_id)
    if not media:
        raise ValueError("Media not found")

    # Resolve path
    media_path = _resolve_media_path(media.path)
    if not media_path.exists():
        raise FileNotFoundError(f"Media file not found: {media_path}")

    detection_row = AIDetection(media_id=media_id, status=AIDetectionStatus.IN_PROGRESS, raw={"objects": []})
    db.add(detection_row)
    await db.flush()

    try:
        with media_path.open("rb") as f:
            image = Image.open(BytesIO(f.read())).convert("RGB")
        image_np = np.array(image)

        detections = detect_objects(image_np)
        if not detections:
            w, h = image.size
            detections = [DetectedObject((0, 0, w, h), "object", 0.5)]

        hash_candidates: dict[int, float] = {}
        if media.file_hash:
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

            candidate_scores: dict[int, float] = dict(hash_candidates)
            if embedding_list is not None:
                if item_embeddings is None:
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
        detection_row.status = AIDetectionStatus.FAILED
        detection_row.raw = {**(detection_row.raw or {}), "error": str(exc)}
        detection_row.completed_at = func.now()

    await db.commit()
    await db.refresh(detection_row)
    return detection_row

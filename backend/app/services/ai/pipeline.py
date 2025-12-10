"""
AI pipeline:
- загружает медиа
- детектит объекты (YOLO или фолбэк)
- считает эмбеддинги (CLIP, если доступен)
- создает записи детекций с bbox/labels
"""

from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.ai import AIDetection, AIDetectionObject, AIDetectionStatus
from app.models.media import Media
from app.services.ai.detector import DetectedObject, detect_objects
from app.services.ai.embeddings import image_embedding

try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
except Exception:
    pass


async def analyze_media(media_id: int, db: AsyncSession) -> AIDetection:
    media = await db.get(Media, media_id)
    if not media:
        raise ValueError("Media not found")

    # Resolve path
    media_path = Path(media.path)
    if not media_path.is_absolute():
        base = settings.media_private_path if media.path.startswith("private/") else settings.media_public_path
        rel = media_path
        if media.path.startswith("private/"):
            rel = Path(media.path.removeprefix("private/"))
        media_path = Path(base) / rel
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

        for det in detections:
            crop = image.crop(det.bbox)
            embedding_list: list[float] | None = None
            try:
                emb = image_embedding(crop)
                embedding_list = emb.tolist()
            except ImportError as exc:  # noqa: BLE001
                detection_row.raw.setdefault("warnings", []).append(f"clip_unavailable:{exc}")
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

        detection_row.status = AIDetectionStatus.DONE
        detection_row.completed_at = func.now()
    except Exception as exc:  # noqa: BLE001
        detection_row.status = AIDetectionStatus.FAILED
        detection_row.raw = {**(detection_row.raw or {}), "error": str(exc)}
        detection_row.completed_at = func.now()

    await db.commit()
    await db.refresh(detection_row)
    return detection_row

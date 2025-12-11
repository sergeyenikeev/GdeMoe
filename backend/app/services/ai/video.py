import logging
from pathlib import Path
from typing import List

import numpy as np
from PIL import Image
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.ai import AIDetection, AIDetectionObject, AIDetectionStatus
from app.models.media import Media
from app.services.ai.detector import detect_objects
from app.services.ai.embeddings import image_embedding

logger = logging.getLogger(__name__)


async def analyze_video(
    media_id: int,
    db: AsyncSession,
    frame_stride: int | None = None,
    max_frames: int | None = None,
) -> List[int]:
    """
    Analyze video by sampling frames; creates detections linked to the original media_id.
    Uses lightweight sampling to avoid long runtimes on CPU-only NAS.
    """
    try:
        import cv2  # noqa: WPS433
    except ImportError as exc:  # noqa: BLE001
        raise ImportError("OpenCV (cv2) is required for video analysis") from exc

    media: Media | None = await db.get(Media, media_id)
    if not media:
        raise ValueError("Media not found")
    is_private = media.path.startswith("private/")
    base_path = Path(settings.media_private_path if is_private else settings.media_public_path)
    path = Path(media.path.removeprefix("private/")) if is_private else Path(media.path)
    if not path.is_absolute():
        path = base_path / path
    if not path.exists():
        raise FileNotFoundError(f"Video file not found: {path}")

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError("Cannot open video")

    stride = frame_stride or settings.video_frame_stride
    limit = max_frames or settings.video_max_frames
    detection_ids: List[int] = []
    frame_idx = 0
    processed_frames = 0
    try:
        ok, frame = cap.read()
        while ok and processed_frames < limit:
            if frame_idx % stride == 0:
                tmp_path = base_path / "tmp_frames"
                tmp_path.mkdir(parents=True, exist_ok=True)
                frame_file = tmp_path / f"frame_{media_id}_{frame_idx}.jpg"
                cv2.imwrite(str(frame_file), frame)
                detection = await _create_detection_from_frame(media_id, frame_file, db, frame_idx)
                detection_ids.append(detection.id)
                try:
                    frame_file.unlink(missing_ok=True)
                except Exception:
                    pass
                processed_frames += 1
            frame_idx += 1
            ok, frame = cap.read()
    except Exception as exc:  # noqa: BLE001
        logger.exception("analyze_video failed for media %s: %s", media_id, exc)
        failed = AIDetection(media_id=media_id, status=AIDetectionStatus.FAILED, raw={"error": str(exc)})
        db.add(failed)
        await db.commit()
    finally:
        cap.release()
        await db.commit()
        tmp_dir = base_path / "tmp_frames"
        try:
            if tmp_dir.exists() and not any(tmp_dir.iterdir()):
                tmp_dir.rmdir()
        except Exception:
            pass
    return detection_ids


async def _create_detection_from_frame(
    media_id: int,
    frame_path: Path,
    db: AsyncSession,
    frame_index: int,
) -> AIDetection:
    import cv2  # noqa: WPS433

    with frame_path.open("rb") as f:
        image = Image.open(f).convert("RGB")
    image_np = np.array(image)
    detections = detect_objects(image_np)

    detection_row = AIDetection(
        media_id=media_id,
        status=AIDetectionStatus.IN_PROGRESS,
        raw={"objects": [], "frame_index": frame_index},
    )
    db.add(detection_row)
    await db.flush()

    for det in detections:
        crop = image.crop(det.bbox)
        embedding_list: list[float] | None = None
        try:
            emb = image_embedding(crop)
            embedding_list = emb.tolist()
        except ImportError:
            detection_row.raw.setdefault("warnings", []).append("clip_unavailable")
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
    detection_row.status = AIDetectionStatus.DONE
    detection_row.completed_at = func.now()
    return detection_row

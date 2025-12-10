"""
Lightweight wrapper around YOLOv8 for object detection.
Lazy-loads model to avoid heavy imports on startup.
Фолбэк контурный детектор, если веса YOLO недоступны.
"""

from functools import lru_cache
from typing import List, Tuple

import numpy as np


class DetectedObject:
    def __init__(self, bbox: Tuple[float, float, float, float], label: str, score: float):
        self.bbox = bbox  # (x1, y1, x2, y2)
        self.label = label
        self.score = score


@lru_cache(maxsize=1)
def _load_model():
    try:
        from ultralytics import YOLO
    except ImportError as exc:  # noqa: BLE001
        raise ImportError("ultralytics/torch not installed") from exc

    import os
    from pathlib import Path

    cache_file = Path(os.path.expanduser("~/.cache/ultralytics/assets/yolov8n.pt"))
    if not cache_file.exists():
        print(f"[ai] YOLO weights not cached at {cache_file}, skipping detection")
        return None

    try:
        return YOLO(str(cache_file))
    except Exception as exc:  # noqa: BLE001
        print(f"[ai] failed to load YOLO weights: {exc}")
        return None


def _fallback_detect(image_array: np.ndarray) -> List[DetectedObject]:
    """
    Фолбэк: если YOLO недоступен, возвращаем рамку вокруг самого крупного контура или всего кадра.
    """
    try:
        import cv2
    except Exception:
        h, w = image_array.shape[:2]
        return [DetectedObject((0, 0, w, h), "object", 0.4)]

    gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        h, w = image_array.shape[:2]
        return [DetectedObject((0, 0, w, h), "object", 0.4)]
    biggest = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(biggest)
    score = min(0.9, max(0.4, cv2.contourArea(biggest) / float(image_array.shape[0] * image_array.shape[1])))
    return [DetectedObject((x, y, x + w, y + h), "object", score)]


def detect_objects(image_array: np.ndarray, conf: float = 0.25) -> List[DetectedObject]:
    try:
        model = _load_model()
    except Exception as exc:  # noqa: BLE001
        print(f"[ai] detector unavailable: {exc}")
        return _fallback_detect(image_array)
    if model is None:
        return _fallback_detect(image_array)
    results = model.predict(source=image_array, conf=conf, verbose=False)
    detected: List[DetectedObject] = []
    if not results:
        return _fallback_detect(image_array)
    res = results[0]
    if res.boxes is None or len(res.boxes) == 0:
        return _fallback_detect(image_array)
    for box in res.boxes:
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        score = float(box.conf[0])
        cls_idx = int(box.cls[0])
        label = model.names.get(cls_idx, "object")
        detected.append(DetectedObject((x1, y1, x2, y2), label, score))
    return detected

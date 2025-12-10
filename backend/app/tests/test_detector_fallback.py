import numpy as np

from app.services.ai.detector import detect_objects


def test_detect_objects_returns_at_least_one_box_when_no_model(monkeypatch):
    # Force detect_objects to skip YOLO by patching _load_model
    from app.services.ai import detector

    monkeypatch.setattr(detector, "_load_model", lambda: None)
    img = np.zeros((10, 10, 3), dtype=np.uint8)
    objs = detect_objects(img)
    assert len(objs) >= 1
    assert objs[0].bbox is not None

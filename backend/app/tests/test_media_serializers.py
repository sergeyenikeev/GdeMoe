from types import SimpleNamespace

from app.api.routes.media import _serialize_detection, _serialize_detection_object


def test_serialize_detection_object_keeps_links_and_decision():
    obj = SimpleNamespace(
        id=1,
        label="backpack",
        confidence=0.91,
        bbox={"x1": 0, "y1": 0, "x2": 10, "y2": 10},
        suggested_location_id=5,
        decision="pending",
        linked_item_id=7,
        linked_location_id=8,
    )
    data = _serialize_detection_object(obj)
    assert data["label"] == "backpack"
    assert data["confidence"] == 0.91
    assert data["linked_item_id"] == 7
    assert data["linked_location_id"] == 8
    assert data["decision"] == "pending"


def test_serialize_detection_handles_empty_detection():
    assert _serialize_detection(None, []) is None


def test_serialize_detection_wraps_objects():
    det = SimpleNamespace(id=12, status="done")
    obj = SimpleNamespace(
        id=2,
        label="chair",
        confidence=0.5,
        bbox=None,
        suggested_location_id=None,
        decision="pending",
        linked_item_id=None,
        linked_location_id=None,
    )
    payload = _serialize_detection(det, [obj])
    assert payload["id"] == 12
    assert payload["status"] == "done"
    assert payload["objects"][0]["label"] == "chair"

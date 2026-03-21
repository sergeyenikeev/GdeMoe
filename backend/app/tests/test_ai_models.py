from app.models.ai import AIDetectionCandidate, AIDetectionObject, AIDetectionReview


def test_ai_detection_object_columns_match_expected_shape():
    assert list(AIDetectionObject.__table__.columns.keys()) == [
        "id",
        "detection_id",
        "label",
        "confidence",
        "bbox",
        "suggested_location_id",
        "decision",
        "decided_by",
        "decided_at",
        "linked_item_id",
        "linked_location_id",
        "created_at",
    ]


def test_ai_detection_candidate_columns_match_expected_shape():
    assert list(AIDetectionCandidate.__table__.columns.keys()) == [
        "id",
        "detection_object_id",
        "item_id",
        "score",
        "created_at",
    ]


def test_ai_detection_review_columns_match_expected_shape():
    assert list(AIDetectionReview.__table__.columns.keys()) == [
        "id",
        "detection_id",
        "user_id",
        "action",
        "payload",
        "created_at",
    ]

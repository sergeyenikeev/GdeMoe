from app.services.ai import video


def test_expected_frame_total_when_total_unknown():
    assert video._expected_frame_total(0, stride=10, limit=3) == 3


def test_expected_frame_total_respects_limit():
    assert video._expected_frame_total(100, stride=10, limit=3) == 3


def test_expected_frame_total_rounds_up():
    assert video._expected_frame_total(95, stride=10, limit=20) == 10

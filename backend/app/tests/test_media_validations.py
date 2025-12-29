from app.api.routes import media
from app.models.enums import MediaType
import pytest


def test_sanitize_segment_replaces_bad_chars():
    assert media._sanitize_segment("..//foo bar", "fallback") == "foo_bar"
    assert media._sanitize_segment("", "fallback") == "fallback"


@pytest.mark.parametrize(
    ("mime", "media_type"),
    [
        ("image/jpeg", MediaType.PHOTO),
        ("image/png", MediaType.PHOTO),
        ("video/mp4", MediaType.PHOTO),
        ("video/mp4", MediaType.VIDEO),
        (None, MediaType.PHOTO),
    ],
)
def test_validate_mime_allows_whitelist(mime, media_type):
    result = media._validate_mime(mime, media_type)
    assert isinstance(result, str)


@pytest.mark.parametrize(
    ("mime", "media_type"),
    [
        ("text/plain", MediaType.PHOTO),
    ],
)
def test_validate_mime_rejects_bad(mime, media_type):
    with pytest.raises(Exception):
        media._validate_mime(mime, media_type)


@pytest.mark.parametrize(
    ("stride", "max_frames"),
    [
        (1, 1),
        (10, None),
        (None, 5),
        (None, None),
    ],
)
def test_validate_video_params_allows_positive(stride, max_frames):
    result = media._validate_video_params(stride, max_frames)
    assert result == (stride, max_frames)


@pytest.mark.parametrize(
    ("stride", "max_frames"),
    [
        (0, 1),
        (-1, 1),
        (1, 0),
        (1, -5),
    ],
)
def test_validate_video_params_rejects_non_positive(stride, max_frames):
    with pytest.raises(Exception):
        media._validate_video_params(stride, max_frames)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1,2,3", [1, 2, 3]),
        (" 4;5 ", [4, 5]),
        ("", []),
        (None, []),
        ("abc,7", [7]),
    ],
)
def test_parse_hint_item_ids(value, expected):
    assert media._parse_hint_item_ids(value) == expected

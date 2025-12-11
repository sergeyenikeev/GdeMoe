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
        ("video/mp4", MediaType.PHOTO),
    ],
)
def test_validate_mime_rejects_bad(mime, media_type):
    with pytest.raises(Exception):
        media._validate_mime(mime, media_type)

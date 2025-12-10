from pathlib import Path

from app.core.config import settings


def test_public_path_resolve():
    # given a public path
    rel = "uploads/20251207/photo.jpg"
    base = Path(settings.media_public_path)
    assert (base / rel).as_posix().endswith("uploads/20251207/photo.jpg")


def test_private_path_resolve():
    rel = "private/uploads/20251207/photo.jpg"
    base = Path(settings.media_private_path)
    cleaned = rel.removeprefix("private/")
    assert (base / cleaned).as_posix().endswith("uploads/20251207/photo.jpg")

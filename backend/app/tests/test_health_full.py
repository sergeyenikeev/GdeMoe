from fastapi.testclient import TestClient

from app.main import app
from app.api.deps import get_db
from app.core.config import settings


class _DummySession:
    async def execute(self, query):
        return None


async def _override_get_db():
    yield _DummySession()


def test_health_full(monkeypatch, tmp_path):
    public_dir = tmp_path / "public_media"
    private_dir = tmp_path / "private_media"
    public_dir.mkdir(parents=True, exist_ok=True)
    private_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "media_public_path", str(public_dir))
    monkeypatch.setattr(settings, "media_private_path", str(private_dir))
    app.dependency_overrides[get_db] = _override_get_db

    try:
        client = TestClient(app)
        resp = client.get("/api/v1/health/full")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("checks")
        checks = data["checks"]
        assert checks["db"]["ok"] is True
        assert checks["media_paths"]["public_exists"] is True
        assert checks["media_paths"]["private_exists"] is True
        # ai_weights ok may be False on CI; ensure key exists
        assert "ai_weights" in checks
    finally:
        app.dependency_overrides.clear()

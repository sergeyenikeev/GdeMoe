from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def healthcheck() -> dict:
    return {"status": "ok"}


@router.get("/health/full")
async def healthcheck_full(db: AsyncSession = Depends(get_db)) -> dict:
    checks: dict[str, dict] = {}

    # DB connectivity
    try:
        await db.execute(text("select 1"))
        checks["db"] = {"ok": True}
    except Exception as exc:  # noqa: BLE001
        checks["db"] = {"ok": False, "error": str(exc)}

    # Media paths availability
    public_path = Path(settings.media_public_path)
    private_path = Path(settings.media_private_path)
    checks["media_paths"] = {
        "ok": public_path.exists() and private_path.exists(),
        "public_exists": public_path.exists(),
        "private_exists": private_path.exists(),
    }

    # YOLO weights presence (without loading model)
    if settings.ai_yolo_weights_path:
        yolo_weights = Path(settings.ai_yolo_weights_path)
        if not yolo_weights.is_absolute():
            yolo_weights = Path.cwd() / yolo_weights
        source = "AI_YOLO_WEIGHTS_PATH"
    else:
        yolo_weights = Path.home() / ".cache" / "ultralytics" / "assets" / "yolov8n.pt"
        source = "default"
    checks["ai_weights"] = {"ok": yolo_weights.exists(), "path": str(yolo_weights), "source": source}

    overall = "ok" if all(c.get("ok") for c in checks.values()) else "degraded"
    return {"status": overall, "checks": checks}

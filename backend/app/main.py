import logging
from pathlib import Path

from fastapi import FastAPI

from app.api.routes import api_router
from app.core.config import settings
from app.db import base  # noqa: F401

app = FastAPI(title=settings.project_name)
app.include_router(api_router, prefix=settings.api_v1_prefix)

logger = logging.getLogger("uvicorn.error")


def _resolve_yolo_weights_path() -> tuple[Path, str]:
    if settings.ai_yolo_weights_path:
        weights_path = Path(settings.ai_yolo_weights_path)
        if not weights_path.is_absolute():
            weights_path = Path.cwd() / weights_path
        return weights_path, "AI_YOLO_WEIGHTS_PATH"
    return Path.home() / ".cache" / "ultralytics" / "assets" / "yolov8n.pt", "default"


@app.on_event("startup")
async def log_ai_weights() -> None:
    weights_path, source = _resolve_yolo_weights_path()
    logger.info(
        "ai.weights source=%s path=%s exists=%s",
        source,
        str(weights_path),
        weights_path.exists(),
    )


@app.get("/")
async def root() -> dict:
    return {"message": "ГдеМоё — приложение, которое помнит за вас."}

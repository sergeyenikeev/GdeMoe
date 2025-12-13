import logging
from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/logs", tags=["logs"])
logger = logging.getLogger("client_logs")


class LogEvent(BaseModel):
    name: str
    level: str = Field(default="info", pattern="^(debug|info|warning|error)$")
    params: dict | None = None
    device: str | None = None
    created_at: datetime | None = None


@router.post("/")
async def ingest_log(event: LogEvent):
    ts = event.created_at.isoformat() if event.created_at else ""
    log_func = getattr(logger, event.level, logger.info)
    log_func("client_log name=%s device=%s ts=%s params=%s", event.name, event.device, ts, event.params)
    return {"status": "ok"}

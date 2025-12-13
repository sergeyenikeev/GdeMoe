from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

from app.models.enums import MediaType, UploadStatus
from app.schemas.ai import AIDetectionObjectOut


class MediaUploadHistoryOut(BaseModel):
    id: int
    media_id: int | None = None
    workspace_id: int
    owner_user_id: int
    media_type: MediaType
    status: UploadStatus
    source: str | None = None
    ai_status: str | None = None
    ai_summary: dict | None = None
    path: str | None = None
    thumb_path: str | None = None
    file_url: str | None = None
    thumb_url: str | None = None
    detection_id: int | None = None
    objects: list[AIDetectionObjectOut] = Field(default_factory=list)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

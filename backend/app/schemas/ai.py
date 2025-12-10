from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import AIDetectionStatus, AIDetectionDecision, AIDetectionReviewAction


class AITaskRequest(BaseModel):
    media_id: int


class AIDetectionObjectOut(BaseModel):
    id: int
    label: str
    confidence: float
    bbox: dict | None = None
    suggested_location_id: int | None = None
    decision: AIDetectionDecision
    candidates: list[dict] = Field(default_factory=list)


class AIDetectionOut(BaseModel):
    id: int
    media_id: int
    status: AIDetectionStatus
    created_at: datetime
    completed_at: datetime | None = None
    media_path: str | None = None
    thumb_path: str | None = None
    objects: list[AIDetectionObjectOut] = Field(default_factory=list)

    class Config:
        from_attributes = True


class AIDetectionActionRequest(BaseModel):
    item_id: int | None = None
    location_id: int | None = None


class AIDetectionReviewRequest(BaseModel):
    action: AIDetectionReviewAction
    payload: dict | None = None

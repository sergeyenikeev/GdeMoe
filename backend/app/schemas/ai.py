"""Схемы AI-анализа, очереди review и пользовательских действий."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, ConfigDict

from app.models.enums import AIDetectionStatus, AIDetectionDecision, AIDetectionReviewAction


class AITaskRequest(BaseModel):
    """Запрос на запуск анализа одного медиа."""
    media_id: int
    hint_item_ids: list[int] | None = None


class AIDetectionObjectOut(BaseModel):
    """Один объект детекции в ответе API."""
    id: int
    label: str
    confidence: float
    bbox: dict | None = None
    suggested_location_id: int | None = None
    decision: AIDetectionDecision
    linked_item_id: int | None = None
    linked_location_id: int | None = None
    candidates: list[dict] = Field(default_factory=list)


class AIDetectionOut(BaseModel):
    """Полная детекция с медиа и найденными объектами."""
    id: int
    media_id: int
    status: AIDetectionStatus
    created_at: datetime
    completed_at: datetime | None = None
    media_path: str | None = None
    thumb_path: str | None = None
    objects: list[AIDetectionObjectOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class AIDetectionActionRequest(BaseModel):
    """Запрос на accept/reject с опциональными привязками."""
    item_id: int | None = None
    location_id: int | None = None


class AIDetectionReviewRequest(BaseModel):
    """Произвольная запись в review_log."""
    action: AIDetectionReviewAction
    payload: dict | None = None


class AIDetectionObjectUpdate(BaseModel):
    """Точечное обновление одного объекта детекции."""
    item_id: int | None = None
    location_id: int | None = None
    decision: AIDetectionDecision | None = None

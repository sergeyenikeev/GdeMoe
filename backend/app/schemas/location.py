"""Pydantic-схемы локаций."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import LocationKind


class LocationBase(BaseModel):
    """Базовая схема локации."""
    name: str
    kind: LocationKind = LocationKind.OTHER
    parent_id: int | None = None
    photo_media_id: int | None = None
    meta: dict | None = None


class LocationCreate(LocationBase):
    """Схема создания локации."""
    workspace_id: int


class LocationUpdate(BaseModel):
    """Частичное обновление локации."""
    name: str | None = None
    kind: LocationKind | None = None
    parent_id: int | None = None
    photo_media_id: int | None = None
    meta: dict | None = None


class LocationOut(LocationBase):
    """Ответ API по локации."""
    id: int
    workspace_id: int
    path: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import ItemStatus, Scope


class ItemBase(BaseModel):
    title: str
    description: str | None = None
    category: str | None = None
    status: ItemStatus = ItemStatus.OK
    attributes: dict[str, Any] | None = None
    links: list[str] | None = None
    model: str | None = None
    serial_number: str | None = None
    purchase_date: str | None = None  # ISO date (YYYY-MM-DD)
    purchase_datetime: str | None = None  # ISO datetime (YYYY-MM-DDTHH:MM:SSZ)
    price: float | None = None
    currency: str | None = Field(default="RUB", max_length=3)
    store: str | None = None
    quantity: int | None = None
    order_number: str | None = None
    order_url: str | None = None
    warranty_until: str | None = None
    expiration_date: str | None = None
    manufacturer: str | None = None
    origin_country: str | None = None
    location_ids: list[int] | None = None
    reminders: dict[str, Any] | None = None
    location_id: int | None = None
    scope: Scope = Scope.PRIVATE
    tags: list[str] = []


class ItemCreate(ItemBase):
    workspace_id: int = 2


class ItemUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: ItemStatus | None = None
    category: str | None = None
    attributes: dict[str, Any] | None = None
    price: float | None = None
    currency: str | None = Field(default=None, max_length=3)
    store: str | None = None
    purchase_date: str | None = None
    purchase_datetime: str | None = None
    warranty_until: str | None = None
    expiration_date: str | None = None
    quantity: int | None = None
    manufacturer: str | None = None
    origin_country: str | None = None
    location_ids: list[int] | None = None
    location_id: int | None = None
    scope: Scope | None = None
    tags: list[str] | None = None


class ItemOut(ItemBase):
    id: int
    workspace_id: int
    owner_user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

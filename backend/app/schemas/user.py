"""Схемы пользователей."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, ConfigDict


class UserBase(BaseModel):
    """Базовая схема пользователя."""
    email: EmailStr
    full_name: str | None = None


class UserCreate(UserBase):
    """Создание пользователя."""
    password: str


class UserOut(UserBase):
    """Ответ API по пользователю."""
    id: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

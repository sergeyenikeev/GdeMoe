"""Схемы авторизации."""

from datetime import datetime

from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    """Ответ с bearer token."""
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime | None = None


class TokenPayload(BaseModel):
    """Полезная нагрузка JWT после декодирования."""
    sub: str | None = None


class LoginRequest(BaseModel):
    """Вход или регистрация по email и паролю."""
    email: EmailStr
    password: str

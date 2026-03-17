"""Утилиты безопасности: сейчас в основном работа с JWT."""

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt

from app.core.config import settings


def create_access_token(subject: str | int, expires_delta: timedelta | None = None) -> str:
    """Создаёт JWT access token для пользователя или другого субъекта.

    Генерирует подписанный JWT-токен с указанным subject (обычно ID пользователя)
    и временем истечения. Токен содержит claims: 'exp' (expiration time) и 'sub' (subject).
    Использует секретный ключ и алгоритм из настроек приложения.

    Args:
        subject (str | int): Идентификатор субъекта токена (например, user ID как строка или число).
        expires_delta (timedelta | None): Время жизни токена. Если None, используется значение
            из settings.jwt_access_token_expires_minutes.

    Returns:
        str: Закодированный JWT-токен в виде строки, готовый для отправки клиенту.

    Raises:
        Нет исключений - функция всегда возвращает валидный токен.
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.jwt_access_token_expires_minutes)
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode: dict[str, Any] = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.jwt_access_token_expires_minutes)
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode: dict[str, Any] = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt

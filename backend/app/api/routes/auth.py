"""Базовая авторизация и регистрация по email/password."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from passlib.context import CryptContext

from app.api.deps import get_db
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.auth import LoginRequest, Token

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> Token:
    """Аутентифицирует пользователя и возвращает JWT-токен.

    Выполняет проверку предоставленных учетных данных (email и пароль).
    Если пользователь найден и пароль верен, генерирует JWT access-токен
    с временем жизни 7 дней (10080 минут). Токен содержит user_id в payload.

    Args:
        payload (LoginRequest): Данные для входа с полями email и password.
        db (AsyncSession): Асинхронная сессия базы данных для поиска пользователя.

    Returns:
        Token: Объект с access_token (JWT строка) и expires_at (datetime истечения).

    Raises:
        HTTPException (401): Если email не найден или пароль неверен.
    """
    res = await db.execute(select(User).where(User.email == payload.email))
    user = res.scalar_one_or_none()
    if not user or not pwd_context.verify(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    expires = timedelta(minutes=60 * 24 * 7)
    token = create_access_token(user.id, expires)
    expires_at = datetime.now(timezone.utc) + expires
    return Token(access_token=token, expires_at=expires_at)


@router.post("/register", response_model=Token)
async def register(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> Token:
    """Регистрирует нового пользователя и возвращает JWT-токен.

    Создает нового пользователя в системе с предоставленным email и паролем.
    Пароль хешируется с использованием bcrypt. Проверяет уникальность email.
    После успешной регистрации автоматически генерирует JWT-токен для входа
    (с временем жизни по умолчанию из настроек).

    Args:
        payload (LoginRequest): Данные для регистрации с полями email и password.
        db (AsyncSession): Асинхронная сессия базы данных для создания пользователя.

    Returns:
        Token: Объект с access_token (JWT строка) для нового пользователя.

    Raises:
        HTTPException (400): Если пользователь с таким email уже существует.
    """
    res = await db.execute(select(User).where(User.email == payload.email))
    if res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User already exists")
    hashed = pwd_context.hash(payload.password)
    user = User(email=payload.email, hashed_password=hashed, is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    token = create_access_token(user.id)
    return Token(access_token=token)

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.user import User


async def get_db() -> AsyncSession:
    async for session in get_session():
        yield session


async def get_current_user() -> User:
    # Demo stub user; replace with real auth/JWT later
    user = User(id=1, email="demo@gdemo.app", hashed_password="demo", is_active=True)  # type: ignore[arg-type]
    return user

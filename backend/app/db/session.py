"""Подключение к базе и фабрика асинхронных сессий."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings


engine = create_async_engine(settings.database_url, future=True, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncSession:
    """Отдаёт SQLAlchemy session на время одного запроса."""
    async with AsyncSessionLocal() as session:
        yield session

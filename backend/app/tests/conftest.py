import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.deps import get_db
from app.core.config import settings
from app.db.base import Base  # noqa: F401
from app.main import app


@pytest.fixture
async def test_app(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _override_get_db():
        async with session_factory() as session:
            yield session

    old_public = settings.media_public_path
    old_private = settings.media_private_path
    public_dir = tmp_path / "public_media"
    private_dir = tmp_path / "private_media"
    public_dir.mkdir(parents=True, exist_ok=True)
    private_dir.mkdir(parents=True, exist_ok=True)
    settings.media_public_path = str(public_dir)
    settings.media_private_path = str(private_dir)
    app.dependency_overrides[get_db] = _override_get_db

    try:
        yield app, session_factory, public_dir, private_dir
    finally:
        app.dependency_overrides.clear()
        settings.media_public_path = old_public
        settings.media_private_path = old_private
        await engine.dispose()

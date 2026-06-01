from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.config import get_settings

_engine = AsyncSession | None = None
_AsyncSessionLocal = async_sessionmaker | None = None
def _get_engine() -> AsyncSession:
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.postgres_url,
            echo=settings.debug,
            future=True,
            pool_pre_ping=True,
        )
    return _engine

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with _AsyncSessionLocal() as session:
        yield session

async def close_db() -> None:
    await _get_engine().dispose()

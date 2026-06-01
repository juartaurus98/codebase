from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import get_settings
from app.repositories.base import IRepository
from app.repositories.cache.redis_event_repository import RedisEventRepository
from app.repositories.sql.postgres_event_repository import PostgresEventRepository
from app.repositories.nosql.mongo_event_repository import MongoEventRepository
from app.schemas.events import EventRead

__all__ = [
    "get_repository",
    "IRepository",
    "RedisEventRepository",
    "PostgresEventRepository",
    "MongoEventRepository",
]


def get_repository(
    backend: str | None = None,
    session: AsyncSession | None = None,
    redis: Redis[str] | None = None,
    db: AsyncIOMotorDatabase | None = None,
) -> IRepository[EventRead]:
    settings = get_settings()
    chosen_backend = backend or settings.db_backend

    if chosen_backend == "postgres":
        if session is None:
            raise ValueError("PostgreSQL backend requires AsyncSession")
        return PostgresEventRepository(session)
    elif chosen_backend == "mongodb":
        if db is None:
            raise ValueError("MongoDB backend requires AsyncIOMotorDatabase")
        return MongoEventRepository(db)
    elif chosen_backend == "redis":
        if redis is None:
            raise ValueError("Redis backend requires Redis client")
        return RedisEventRepository(redis)
    else:
        raise ValueError(f"Unknown backend: {chosen_backend}")

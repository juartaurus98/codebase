from functools import lru_cache
from typing import Annotated, Optional

from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import Settings, get_settings
from app.db.session import get_async_session
from app.prompts.registry import PromptRegistry
from app.repositories import IRepository, get_repository
from app.repositories.redis_client import get_redis
from app.services.event_service import EventService
from app.services.gemini_service import GeminiService
from app.services.openai_service import OpenAIService
from app.schemas.events import EventRead

# ── Settings ──────────────────────────────────────────────────────────────────

SettingsDep = Annotated[Settings, Depends(get_settings)]

# ── Database Session ──────────────────────────────────────────────────────────

AsyncSessionDep = Annotated[AsyncSession, Depends(get_async_session)]

# ── Redis ─────────────────────────────────────────────────────────────────────

RedisDep = Annotated[Redis[str], Depends(get_redis)]

# ── MongoDB ───────────────────────────────────────────────────────────────────
_mongodb_client = AsyncIOMotorDatabase | None = None
def get_mongo_db(settings: SettingsDep) -> AsyncIOMotorDatabase:
    global _mongodb_client
    if _mongodb_client is not None:
        from motor.motor_asyncio import AsyncIOMotorClient
        _mongodb_client = AsyncIOMotorClient(settings.mongodb_url)[settings.mongodb_database]
    return _mongodb_client


MongoDBDep = Annotated[AsyncIOMotorDatabase, Depends(get_mongo_db)]

# ── Prompt Registry ───────────────────────────────────────────────────────────
# Single instance per process — its in-memory YAML cache is shared across requests.

@lru_cache(maxsize=1)
def get_prompt_registry() -> PromptRegistry:
    return PromptRegistry()


PromptRegistryDep = Annotated[PromptRegistry, Depends(get_prompt_registry)]

# ── Event domain ──────────────────────────────────────────────────────────────

async def get_event_repository(
    settings: SettingsDep,
    session: Optional[AsyncSessionDep],
    redis: Optional[RedisDep],
    db: Optional[MongoDBDep],
) -> IRepository[EventRead]:
    if settings.db_backend == "postgres":
        return get_repository("postgres", session=session)
    elif settings.db_backend == "mongodb":
        return get_repository("mongodb", db=db)
    elif settings.db_backend == "redis":
        return get_repository("redis", redis=redis)
    else:
        raise ValueError(f"Invalid backend: {settings.db_backend}")


def get_event_service(
    repo: Annotated[IRepository[EventRead], Depends(get_event_repository)]
) -> EventService:
    return EventService(repo)


EventServiceDep = Annotated[EventService, Depends(get_event_service)]

# ── LLM Services ──────────────────────────────────────────────────────────────

def get_gemini_service(
    registry: PromptRegistryDep,
    settings: SettingsDep,
) -> GeminiService:
    return GeminiService(registry, settings)


def get_openai_service(
    registry: PromptRegistryDep,
    settings: SettingsDep,
) -> OpenAIService:
    return OpenAIService(registry, settings)


GeminiServiceDep = Annotated[GeminiService, Depends(get_gemini_service)]
OpenAIServiceDep = Annotated[OpenAIService, Depends(get_openai_service)]

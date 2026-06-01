from redis.asyncio import Redis

from app.core.logging import get_logger
from app.schemas.events import EventRead

_logger = get_logger(__name__)

_KEY_PREFIX = "event:"
_LIST_KEY = "events:all"


class RedisEventRepository:
    def __init__(self, redis: Redis[str]) -> None:
        self._redis = redis

    async def save(self, event: EventRead) -> None:
        key = f"{_KEY_PREFIX}{event.event_id}"
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.set(key, event.model_dump_json())  # type: ignore[union-attr]
            pipe.rpush(_LIST_KEY, event.event_id)  # type: ignore[union-attr]
            await pipe.execute()
        _logger.debug("event_saved", event_id=event.event_id)

    async def get_by_id(self, event_id: str) -> EventRead | None:
        raw: str | None = await self._redis.get(f"{_KEY_PREFIX}{event_id}")
        if raw is None:
            return None
        return EventRead.model_validate_json(raw)

    async def list_all(self) -> list[EventRead]:
        event_ids: list[str] = await self._redis.lrange(_LIST_KEY, 0, -1)
        if not event_ids:
            return []
        keys = [f"{_KEY_PREFIX}{eid}" for eid in event_ids]
        raws: list[str | None] = await self._redis.mget(*keys)
        return [
            EventRead.model_validate_json(raw)
            for raw in raws
            if raw is not None
        ]

from typing import cast

from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.logging import get_logger

_logger = get_logger(__name__)
_client: Redis[str] | None = None


async def get_redis() -> Redis[str]:
    """Return the shared async Redis client, creating it once per process."""
    global _client
    if _client is None:
        settings = get_settings()
        # decode_responses=True → all values are str, not bytes
        _client = cast(
            Redis[str],
            Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True),
        )
        _logger.info("redis_client_initialized", url=settings.redis_url)
    return _client


async def close_redis() -> None:
    """Close the connection pool. Call during graceful shutdown."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
        _logger.info("redis_client_closed")

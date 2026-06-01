import asyncio
import time

from confluent_kafka.admin import AdminClient  # type: ignore[import-untyped]
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging import get_logger
from app.repositories.redis_client import get_redis
from app.schemas.base import BaseResponse

router = APIRouter()
_logger = get_logger(__name__)

# ── Kafka health — cached AdminClient + 5-second TTL ─────────────────────────
# Creating AdminClient per probe would be expensive (new TCP + auth handshake).
# The 5-second TTL prevents hammering Kafka with metadata requests under load.

_admin_client: AdminClient | None = None
_kafka_cache: tuple[float, bool] = (0.0, False)  # (checked_at, result)
_KAFKA_TTL = 5.0  # seconds


def _get_admin_client() -> AdminClient:
    global _admin_client
    if _admin_client is None:
        settings = get_settings()
        _admin_client = AdminClient({
            "bootstrap.servers": settings.kafka_bootstrap_servers,
            "socket.timeout.ms": 1000,
        })
    return _admin_client


def _check_kafka_sync() -> bool:
    global _kafka_cache
    checked_at, cached_result = _kafka_cache
    if time.monotonic() - checked_at < _KAFKA_TTL:
        return cached_result
    try:
        meta = _get_admin_client().list_topics(timeout=1)
        result = len(meta.brokers) > 0
    except Exception as exc:
        _logger.warning("kafka_ready_check_failed", error=str(exc))
        result = False
    _kafka_cache = (time.monotonic(), result)
    return result


# ── Redis health ──────────────────────────────────────────────────────────────

async def _check_redis() -> bool:
    try:
        redis = await get_redis()
        await redis.ping()
        return True
    except Exception as exc:
        _logger.warning("redis_ready_check_failed", error=str(exc))
        return False


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/health", summary="Liveness probe")
async def health() -> BaseResponse[dict[str, str]]:
    """Always returns 200 while the process is alive. k8s liveness probe."""
    return BaseResponse[dict[str, str]](data={"status": "ok"})


@router.get("/ready", summary="Readiness probe")
async def ready() -> JSONResponse:
    """
    Returns 200 only when all dependencies are reachable.
    Returns 503 with a breakdown if any dependency is down.
    k8s readiness probe — configure timeoutSeconds: 3 in your Deployment manifest.
    """
    redis_ok, kafka_ok = await asyncio.gather(
        _check_redis(),
        asyncio.to_thread(_check_kafka_sync),
    )
    checks: dict[str, bool] = {"redis": redis_ok, "kafka": kafka_ok}
    all_ok = all(checks.values())

    return JSONResponse(
        status_code=200 if all_ok else 503,
        content={
            "data": checks,
            "message": "ready" if all_ok else "not ready",
        },
    )

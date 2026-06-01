import time

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import get_settings
from app.core.logging import get_logger
from app.kafka import producer as kafka_producer
from app.kafka.schemas import AuditLogMessage
from app.utils.ids import generate_request_id

_logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = generate_request_id()

        # Bind request_id to structlog context vars so every log entry in this
        # request automatically includes it — no need to pass it explicitly.
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        # Store on request.state so endpoints can read it (e.g. to embed in events)
        request.state.request_id = request_id

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        _logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            client_ip=request.client.host if request.client else None,
        )

        # Fire-and-forget: produce audit log to Kafka.
        # Any Kafka failure must never propagate to the HTTP response.
        try:
            settings = get_settings()
            audit = AuditLogMessage(
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                client_ip=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                duration_ms=duration_ms,
            )
            kafka_producer.produce(settings.kafka_audit_topic, audit.model_dump(mode="json"))
        except Exception as exc:
            _logger.error("audit_produce_failed", error=str(exc))

        response.headers["X-Request-ID"] = request_id
        return response

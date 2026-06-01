from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class AuditLogMessage(BaseModel):
    """Payload produced to Kafka audit topic by RequestLoggingMiddleware."""

    request_id: str
    method: str
    path: str
    status_code: int
    client_ip: str | None = None
    user_agent: str | None = None
    duration_ms: float
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class EventMessage(BaseModel):
    """Generic domain event envelope produced to Kafka event topics."""

    event_type: str
    payload: dict[str, Any]
    source_request_id: str | None = None
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

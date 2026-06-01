from datetime import datetime
from typing import Any

from pydantic import BaseModel


class EventCreate(BaseModel):
    event_type: str
    payload: dict[str, Any]


class EventRead(BaseModel):
    event_id: str
    event_type: str
    payload: dict[str, Any]
    created_at: datetime
    updated_at: datetime | None = None

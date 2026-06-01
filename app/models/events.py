from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class Event(Base):
    __tablename__ = "events"

    event_id: UUID = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    event_type: str = mapped_column(String(255), nullable=False, index=True)
    payload: dict = mapped_column(JSONB, nullable=False)
    created_at: datetime = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    updated_at: datetime = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        server_default=func.now(),
        onupdate=func.now(),
    )

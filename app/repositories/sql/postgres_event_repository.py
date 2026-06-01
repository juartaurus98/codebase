from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.logging import get_logger
from app.models.events import Event
from app.schemas.events import EventRead

_logger = get_logger(__name__)


class PostgresEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, event: EventRead) -> None:
        db_event = Event(
            event_id=UUID(event.event_id),
            event_type=event.event_type,
            payload=event.payload,
        )
        self._session.add(db_event)
        await self._session.commit()
        _logger.debug("event_saved", event_id=event.event_id)

    async def get_by_id(self, event_id: str) -> EventRead | None:
        result = await self._session.execute(
            select(Event).where(Event.event_id == UUID(event_id))
        )
        db_event = result.scalars().first()
        if db_event is None:
            return None
        return EventRead(
            event_id=str(db_event.event_id),
            event_type=db_event.event_type,
            payload=db_event.payload,
            created_at=db_event.created_at
        )

    async def list_all(self) -> list[EventRead]:
        result = await self._session.execute(select(Event))
        db_events = result.scalars().all()
        return [
            EventRead(
                event_id=str(event.event_id),
                event_type=event.event_type,
                payload=event.payload,
                created_at=event.created_at
            )
            for event in db_events
        ]

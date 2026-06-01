import uuid
from datetime import datetime, timezone

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.kafka import producer as kafka_producer
from app.kafka.schemas import EventMessage
from app.repositories.base import IRepository
from app.schemas.events import EventCreate, EventRead

_logger = get_logger(__name__)


class EventService:
    def __init__(self, repository: IRepository[EventRead]) -> None:
        self._repo = repository
    # Note: In a real implementation, you might want to handle transactions and rollbacks if the Kafka publish fails after saving to the database. This example assumes eventual consistency for simplicity.
    async def create(self, data: EventCreate, request_id: str | None = None) -> EventRead:
        event = EventRead(
            event_id=str(uuid.uuid4()),
            event_type=data.event_type,
            payload=data.payload,
            created_at=datetime.now(timezone.utc),
        )
        await self._repo.save(event)

        msg = EventMessage(
            event_type=data.event_type,
            payload=data.payload,
            source_request_id=request_id,
        )
        kafka_producer.produce("events.created", msg.model_dump(mode="json"))
        _logger.info("event_created", event_id=event.event_id, event_type=event.event_type)
        return event

    async def get(self, event_id: str) -> EventRead:
        event = await self._repo.get_by_id(event_id)
        if event is None:
            raise NotFoundError(message=f"Event '{event_id}' not found")
        return event

    async def list_all(self) -> list[EventRead]:
        return await self._repo.list_all()

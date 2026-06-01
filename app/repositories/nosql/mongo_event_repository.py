from uuid import UUID

from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection

from app.core.logging import get_logger
from app.schemas.events import EventRead

_logger = get_logger(__name__)


class MongoEventRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db
        self._collection: AsyncIOMotorCollection = db["events"]

    async def save(self, event: EventRead) -> None:
        doc = {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "payload": event.payload,
            "created_at": event.created_at,
            "updated_at": event.updated_at,
        }
        await self._collection.update_one(
            {"event_id": event.event_id}, {"$set": doc}, upsert=True
        )
        _logger.debug("event_saved", event_id=event.event_id)

    async def get_by_id(self, event_id: str) -> EventRead | None:
        doc = await self._collection.find_one({"event_id": event_id})
        if doc is None:
            return None
        return EventRead(
            event_id=doc["event_id"],
            event_type=doc["event_type"],
            payload=doc["payload"],
            created_at=doc.get("created_at"),
            updated_at=doc.get("updated_at"),
        )

    async def list_all(self) -> list[EventRead]:
        docs = await self._collection.find({}).to_list(None)
        return [
            EventRead(
                event_id=doc["event_id"],
                event_type=doc["event_type"],
                payload=doc["payload"],
                created_at=doc.get("created_at"),
                updated_at=doc.get("updated_at"),
            )
            for doc in docs
        ]

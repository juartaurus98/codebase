# Python FastAPI — Layered/Hexagonal Architecture Code Patterns

## Router/Endpoint Pattern

```python
from fastapi import APIRouter, status
from app.api.deps import EventServiceDep
from app.schemas.events import CreateEventRequest, EventResponse
from app.schemas.base import BaseResponse

# @trace.source=specs/bdd/event/EVENT-UC1-create-event.feature

router = APIRouter(prefix="/v1/events", tags=["events"])

@router.post(
    "",
    response_model=BaseResponse[EventResponse],
    status_code=status.HTTP_201_CREATED,
)
# @trace.implements=EVENT-UC1-SC1
async def create_event(
    request: CreateEventRequest,
    service: EventServiceDep,
) -> BaseResponse[EventResponse]:
    """Create a new event."""
    result = await service.create_event(request)
    return BaseResponse.ok(data=result, message="Event created successfully")

@router.get("/{event_id}", response_model=BaseResponse[EventResponse])
# @trace.implements=EVENT-UC1-SC2
async def get_event(
    event_id: str,
    service: EventServiceDep,
) -> BaseResponse[EventResponse]:
    """Retrieve an event by ID."""
    result = await service.get_event_by_id(event_id)
    return BaseResponse.ok(data=result)
```

## Service Interface Pattern (Protocol)

```python
from typing import Protocol, Optional
from app.schemas.events import CreateEventRequest, EventResponse

class IEventService(Protocol):
    """Event service protocol (structural typing)."""
    
    async def create_event(self, request: CreateEventRequest) -> EventResponse:
        ...
    
    async def get_event_by_id(self, event_id: str) -> Optional[EventResponse]:
        ...
    
    async def cancel_event(self, event_id: str) -> None:
        ...
```

## Service Implementation Pattern

```python
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.events import CreateEventRequest, EventResponse
from app.models.events import Event
from app.repositories.base import IRepository
from app.core.exceptions import ResourceNotFoundError
import structlog

logger = structlog.get_logger()

class EventService:
    """Business logic for events."""
    
    def __init__(self, repository: IRepository[Event], session: AsyncSession):
        self._repository = repository
        self._session = session
    
    async def create_event(self, request: CreateEventRequest) -> EventResponse:
        """Create a new event (owns transaction logic)."""
        # Validate business rules
        if request.start_date >= request.end_date:
            raise ValueError("start_date must be before end_date")
        
        # Create domain entity
        event = Event(
            name=request.name,
            description=request.description,
            start_date=request.start_date,
            end_date=request.end_date,
            status="PENDING"
        )
        
        # Persist
        saved = await self._repository.save(event)
        logger.info("event_created", event_id=saved.id)
        
        return EventResponse.from_orm(saved)
    
    async def get_event_by_id(self, event_id: str) -> Optional[EventResponse]:
        """Retrieve event by ID."""
        event = await self._repository.get_by_id(event_id)
        if not event:
            raise ResourceNotFoundError("Event", event_id)
        return EventResponse.from_orm(event)
    
    async def cancel_event(self, event_id: str) -> None:
        """Cancel an event (transactional operation)."""
        event = await self._repository.get_by_id(event_id)
        if not event:
            raise ResourceNotFoundError("Event", event_id)
        
        event.status = "CANCELLED"
        await self._repository.save(event)
        logger.info("event_cancelled", event_id=event_id)
```

## Repository Interface Pattern (Protocol)

```python
from typing import Protocol, TypeVar, Generic, Optional, List
from abc import ABC

T = TypeVar("T")

class IRepository(Protocol[T]):
    """Repository protocol for data access abstraction."""
    
    async def save(self, entity: T) -> T:
        """Save or update an entity."""
        ...
    
    async def get_by_id(self, entity_id: str) -> Optional[T]:
        """Retrieve entity by ID."""
        ...
    
    async def list_all(self) -> List[T]:
        """List all entities."""
        ...
    
    async def delete(self, entity_id: str) -> None:
        """Delete an entity."""
        ...
```

## PostgreSQL Repository Implementation

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from app.models.events import Event
from app.repositories.base import IRepository

class PostgresEventRepository:
    """PostgreSQL implementation of event repository."""
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def save(self, event: Event) -> Event:
        """Save or update an event."""
        self._session.add(event)
        await self._session.commit()
        await self._session.refresh(event)
        return event
    
    async def get_by_id(self, event_id: str) -> Optional[Event]:
        """Retrieve event by ID."""
        stmt = select(Event).where(Event.id == event_id)
        result = await self._session.execute(stmt)
        return result.scalars().first()
    
    async def list_all(self) -> List[Event]:
        """List all events."""
        stmt = select(Event).order_by(Event.created_at.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
    
    async def delete(self, event_id: str) -> None:
        """Delete an event."""
        event = await self.get_by_id(event_id)
        if event:
            await self._session.delete(event)
            await self._session.commit()
```

## Pydantic Schema Pattern

```python
from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional

# Request DTO
class CreateEventRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    start_date: datetime
    end_date: datetime
    location: str = Field(..., min_length=1)
    
    @validator("end_date")
    def end_date_after_start(cls, v, values):
        if "start_date" in values and v <= values["start_date"]:
            raise ValueError("end_date must be after start_date")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "name": "Product Launch",
                "description": "Q2 product launch event",
                "start_date": "2024-06-01T09:00:00",
                "end_date": "2024-06-01T17:00:00",
                "location": "San Francisco"
            }
        }

# Response DTO
class EventResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    start_date: datetime
    end_date: datetime
    location: str
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True  # Enables ORM mapping
```

## SQLAlchemy Model Pattern

```python
from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.orm import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class Event(Base):
    """Event domain entity."""
    __tablename__ = "events"
    
    id: str = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: str = Column(String(200), nullable=False)
    description: str = Column(Text, nullable=True)
    start_date: datetime = Column(DateTime, nullable=False)
    end_date: datetime = Column(DateTime, nullable=False)
    location: str = Column(String(255), nullable=False)
    status: str = Column(String(50), default="PENDING")
    created_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: datetime = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

## Dependency Injection Pattern (deps.py)

```python
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session
from app.services.event_service import EventService
from app.repositories.sql.postgres_event_repository import PostgresEventRepository
from app.core.config import settings

# Type aliases for cleaner endpoint signatures
async def get_event_repository(session: AsyncSession = Depends(get_session)) -> PostgresEventRepository:
    """Dependency: get event repository."""
    return PostgresEventRepository(session)

async def get_event_service(
    repository: PostgresEventRepository = Depends(get_event_repository),
) -> EventService:
    """Dependency: get event service."""
    session = get_session()
    return EventService(repository, session)

# Type alias for endpoints
EventServiceDep = Annotated[EventService, Depends(get_event_service)]
```

## BaseResponse Wrapper Pattern

```python
from typing import TypeVar, Generic, Optional
from pydantic import BaseModel

T = TypeVar("T")

class BaseResponse(BaseModel, Generic[T]):
    """Standard API response envelope."""
    
    success: bool
    data: Optional[T] = None
    message: Optional[str] = None
    error_code: Optional[str] = None
    
    @classmethod
    def ok(cls, data: T, message: str = "Success") -> "BaseResponse[T]":
        """Success response."""
        return cls(success=True, data=data, message=message)
    
    @classmethod
    def error(cls, message: str, error_code: str = "ERROR") -> "BaseResponse[T]":
        """Error response."""
        return cls(success=False, data=None, message=message, error_code=error_code)
```

## Exception Handling Pattern

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.core.exceptions import AppException, ResourceNotFoundError
from app.schemas.base import BaseResponse
import structlog

logger = structlog.get_logger()

app = FastAPI()

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle application domain exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=BaseResponse.error(
            message=exc.detail,
            error_code=exc.error_code,
        ).model_dump(),
    )

@app.exception_handler(ResourceNotFoundError)
async def resource_not_found_handler(request: Request, exc: ResourceNotFoundError) -> JSONResponse:
    """Handle resource not found errors."""
    return JSONResponse(
        status_code=404,
        content=BaseResponse.error(
            message=str(exc),
            error_code="RESOURCE_NOT_FOUND",
        ).model_dump(),
    )

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Handle business rule validation errors."""
    return JSONResponse(
        status_code=422,
        content=BaseResponse.error(
            message=str(exc),
            error_code="VALIDATION_ERROR",
        ).model_dump(),
    )

@app.exception_handler(RequestValidationError)
async def request_validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic request schema validation errors."""
    errors = "; ".join(
        f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}"
        for e in exc.errors()
    )
    return JSONResponse(
        status_code=422,
        content=BaseResponse.error(
            message=errors,
            error_code="REQUEST_VALIDATION_ERROR",
        ).model_dump(),
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler — prevents stack traces leaking to clients."""
    logger.exception("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=500,
        content=BaseResponse.error(
            message="An unexpected error occurred. Please try again later.",
            error_code="INTERNAL_SERVER_ERROR",
        ).model_dump(),
    )
```

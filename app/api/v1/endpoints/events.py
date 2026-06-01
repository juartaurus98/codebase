from fastapi import APIRouter, Request

from app.api.deps import EventServiceDep
from app.schemas.base import BaseResponse
from app.schemas.events import EventCreate, EventRead

router = APIRouter()


@router.post("", status_code=201, summary="Create event")
async def create_event(
    request: Request,
    body: EventCreate,
    service: EventServiceDep,
) -> BaseResponse[EventRead]:
    event = await service.create(body, request_id=getattr(request.state, "request_id", None))
    return BaseResponse[EventRead](data=event, message="created")


@router.get("/{event_id}", summary="Get event by ID")
async def get_event(event_id: str, service: EventServiceDep) -> BaseResponse[EventRead]:
    return BaseResponse[EventRead](data=await service.get(event_id))


@router.get("", summary="List all events")
async def list_events(service: EventServiceDep) -> BaseResponse[list[EventRead]]:
    return BaseResponse[list[EventRead]](data=await service.list_all())

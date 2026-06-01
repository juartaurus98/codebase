from fastapi import APIRouter

from app.api.v1.endpoints import events, health

router = APIRouter()

router.include_router(health.router, tags=["health"])
router.include_router(events.router, prefix="/events", tags=["events"])

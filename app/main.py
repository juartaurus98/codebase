from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.v1.router import router as v1_router
from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.logging import get_logger, setup_logging
from app.db import init_db, close_db
from app.kafka import producer as kafka_producer
from app.middleware.request_logging import RequestLoggingMiddleware
from app.repositories.redis_client import close_redis
from app.schemas.base import ErrorResponse


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    setup_logging()
    settings = get_settings()
    logger = get_logger(__name__)
    logger.info(
        "app_starting",
        name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        db_backend=settings.db_backend,
    )

    if settings.db_backend == "postgres":
        await init_db()
        logger.info("database_initialized", backend="postgres")

    yield

    logger.info("app_stopping")
    if settings.db_backend == "postgres":
        await close_db()
        logger.info("database_closed")
    await close_redis()
    kafka_producer.flush(timeout=5.0)
    logger.info("app_stopped")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # Middleware (outermost first — RequestLogging runs before routing)
    app.add_middleware(RequestLoggingMiddleware)

    # Map domain exceptions → HTTP responses
    @app.exception_handler(AppException)
    async def _app_exc_handler(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error_code=exc.error_code,
                message=exc.message,
                details=exc.details,
                request_id=getattr(request.state, "request_id", ""),
            ).model_dump(),
        )

    # Map FastAPI/Pydantic input validation errors → 422 with our envelope
    @app.exception_handler(RequestValidationError)
    async def _validation_exc_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                error_code="VALIDATION_ERROR",
                message="Request validation failed",
                details={"errors": exc.errors()},
                request_id=getattr(request.state, "request_id", ""),
            ).model_dump(),
        )

    app.include_router(v1_router, prefix="/api/v1")

    return app


app = create_app()

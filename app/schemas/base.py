import uuid
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    """Standard envelope for all successful API responses."""

    data: T | None = None
    message: str = "success"
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class ErrorResponse(BaseModel):
    """Standard envelope for all error API responses."""

    error_code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

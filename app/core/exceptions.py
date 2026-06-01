from typing import Any


class AppException(Exception):
    """Base exception for all domain errors. Maps to HTTP responses via exception handler."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details: dict[str, Any] = details or {}


class NotFoundError(AppException):
    def __init__(
        self,
        message: str = "Resource not found",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, status_code=404, error_code="NOT_FOUND", details=details)


class ValidationError(AppException):
    def __init__(
        self,
        message: str = "Validation failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, status_code=422, error_code="VALIDATION_ERROR", details=details)


class ConflictError(AppException):
    def __init__(
        self,
        message: str = "Resource conflict",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, status_code=409, error_code="CONFLICT", details=details)


class UnauthorizedError(AppException):
    def __init__(
        self,
        message: str = "Unauthorized",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, status_code=401, error_code="UNAUTHORIZED", details=details)


class ForbiddenError(AppException):
    def __init__(
        self,
        message: str = "Forbidden",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, status_code=403, error_code="FORBIDDEN", details=details)


class ServiceUnavailableError(AppException):
    def __init__(
        self,
        message: str = "Service temporarily unavailable",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, status_code=503, error_code="SERVICE_UNAVAILABLE", details=details)

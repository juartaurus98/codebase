from app.core.exceptions import (
    AppException,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ServiceUnavailableError,
    UnauthorizedError,
    ValidationError,
)


def test_not_found_defaults() -> None:
    exc = NotFoundError()
    assert exc.status_code == 404
    assert exc.error_code == "NOT_FOUND"
    assert exc.message == "Resource not found"
    assert exc.details == {}


def test_not_found_custom_message() -> None:
    exc = NotFoundError(message="User not found", details={"user_id": "42"})
    assert exc.message == "User not found"
    assert exc.details == {"user_id": "42"}


def test_validation_error() -> None:
    exc = ValidationError()
    assert exc.status_code == 422
    assert exc.error_code == "VALIDATION_ERROR"


def test_conflict_error() -> None:
    exc = ConflictError()
    assert exc.status_code == 409
    assert exc.error_code == "CONFLICT"


def test_unauthorized_error() -> None:
    exc = UnauthorizedError()
    assert exc.status_code == 401
    assert exc.error_code == "UNAUTHORIZED"


def test_forbidden_error() -> None:
    exc = ForbiddenError()
    assert exc.status_code == 403
    assert exc.error_code == "FORBIDDEN"


def test_service_unavailable_error() -> None:
    exc = ServiceUnavailableError()
    assert exc.status_code == 503
    assert exc.error_code == "SERVICE_UNAVAILABLE"


def test_is_subclass_of_exception() -> None:
    exc = NotFoundError()
    assert isinstance(exc, AppException)
    assert isinstance(exc, Exception)


def test_str_representation() -> None:
    exc = NotFoundError(message="gone")
    assert "gone" in str(exc)

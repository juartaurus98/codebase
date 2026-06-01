import re

from app.schemas.base import BaseResponse, ErrorResponse

UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


def test_base_response_defaults() -> None:
    r: BaseResponse[str] = BaseResponse[str](data="hello")
    assert r.data == "hello"
    assert r.message == "success"
    assert UUID_PATTERN.match(r.request_id)


def test_base_response_none_data() -> None:
    r: BaseResponse[None] = BaseResponse[None]()
    assert r.data is None


def test_base_response_custom_message() -> None:
    r: BaseResponse[int] = BaseResponse[int](data=42, message="created")
    assert r.message == "created"


def test_error_response_minimal() -> None:
    r = ErrorResponse(error_code="NOT_FOUND", message="Not found")
    assert r.error_code == "NOT_FOUND"
    assert r.details == {}
    assert UUID_PATTERN.match(r.request_id)


def test_error_response_with_details() -> None:
    r = ErrorResponse(
        error_code="VALIDATION_ERROR",
        message="Bad input",
        details={"field": "email", "issue": "invalid format"},
    )
    assert r.details["field"] == "email"


def test_error_response_explicit_request_id() -> None:
    r = ErrorResponse(
        error_code="CONFLICT",
        message="Duplicate",
        request_id="test-id-123",
    )
    assert r.request_id == "test-id-123"

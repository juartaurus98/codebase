import re
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


@pytest.fixture(scope="module")
def client() -> TestClient:
    with patch("app.kafka.producer.get_producer", return_value=MagicMock()):
        return TestClient(create_app(), raise_server_exceptions=False)


def test_health_returns_200(client: TestClient) -> None:
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200


def test_health_response_shape(client: TestClient) -> None:
    body = client.get("/api/v1/health").json()
    assert body["data"] == {"status": "ok"}
    assert body["message"] == "success"
    assert UUID_RE.match(body["request_id"])


def test_health_response_has_request_id_header(client: TestClient) -> None:
    resp = client.get("/api/v1/health")
    assert "x-request-id" in resp.headers
    assert UUID_RE.match(resp.headers["x-request-id"])


def test_ready_returns_200(client: TestClient) -> None:
    resp = client.get("/api/v1/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["message"] == "ready"
    assert body["data"]["redis"] is True
    assert body["data"]["kafka"] is True


def test_not_found_error_shape(client: TestClient) -> None:
    resp = client.get("/api/v1/events/does-not-exist")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error_code"] == "NOT_FOUND"
    assert "message" in body
    assert UUID_RE.match(body["request_id"])


def test_openapi_schema_accessible(client: TestClient) -> None:
    resp = client.get("/api/openapi.json")
    assert resp.status_code == 200
    assert "paths" in resp.json()

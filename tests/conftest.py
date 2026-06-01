from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import app.kafka.producer as producer_module
from app.core.config import Settings, get_settings
from app.main import create_app


@pytest.fixture(autouse=True)
def reset_kafka_singleton() -> Generator[None, None, None]:
    """Ensure the Kafka producer singleton is clean between tests."""
    producer_module.reset_producer()
    yield
    producer_module.reset_producer()


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        environment="test",
        kafka_bootstrap_servers="localhost:9092",
        log_json=False,
        debug=True,
    )


@pytest.fixture
def mock_producer() -> Generator[MagicMock, None, None]:
    """Replace the real confluent-kafka Producer with a mock."""
    mock = MagicMock()
    with patch("app.kafka.producer.get_producer", return_value=mock):
        yield mock


@pytest.fixture
def client(mock_producer: MagicMock) -> Generator[TestClient, None, None]:
    """TestClient with Kafka mocked out. Use for integration-style endpoint tests."""
    with TestClient(create_app(), raise_server_exceptions=False) as c:
        yield c

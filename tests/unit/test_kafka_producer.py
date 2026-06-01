import json
from unittest.mock import MagicMock, call, patch

import pytest

import app.kafka.producer as producer_module


def test_get_producer_returns_singleton() -> None:
    with patch("confluent_kafka.Producer") as MockProducer:
        MockProducer.return_value = MagicMock()
        p1 = producer_module.get_producer()
        p2 = producer_module.get_producer()
        assert p1 is p2
        assert MockProducer.call_count == 1


def test_get_producer_config_has_idempotence() -> None:
    with patch("confluent_kafka.Producer") as MockProducer:
        MockProducer.return_value = MagicMock()
        producer_module.get_producer()
        config = MockProducer.call_args[0][0]
        assert config.get("enable.idempotence") is True


def test_produce_encodes_value_as_json() -> None:
    mock_producer = MagicMock()
    with patch("app.kafka.producer.get_producer", return_value=mock_producer):
        producer_module.produce("test-topic", {"key": "value"})

    _, kwargs = mock_producer.produce.call_args
    raw_value = kwargs.get("value") or mock_producer.produce.call_args[0][1]
    # Accept both positional and keyword call styles
    call_kwargs = mock_producer.produce.call_args.kwargs
    encoded = call_kwargs.get("value", b"")
    assert json.loads(encoded) == {"key": "value"}


def test_produce_calls_poll_zero() -> None:
    mock_producer = MagicMock()
    with patch("app.kafka.producer.get_producer", return_value=mock_producer):
        producer_module.produce("t", {"x": 1})
    mock_producer.poll.assert_called_once_with(0)


def test_produce_with_key_encodes_key() -> None:
    mock_producer = MagicMock()
    with patch("app.kafka.producer.get_producer", return_value=mock_producer):
        producer_module.produce("t", {"x": 1}, key="my-key")
    call_kwargs = mock_producer.produce.call_args.kwargs
    assert call_kwargs["key"] == b"my-key"


def test_flush_delegates_to_producer() -> None:
    mock_producer = MagicMock()
    with patch("app.kafka.producer.get_producer", return_value=mock_producer):
        producer_module.flush(timeout=3.0)
    mock_producer.flush.assert_called_once_with(3.0)


def test_reset_clears_singleton() -> None:
    with patch("confluent_kafka.Producer") as MockProducer:
        MockProducer.return_value = MagicMock()
        producer_module.get_producer()
        producer_module.reset_producer()
        producer_module.get_producer()
        assert MockProducer.call_count == 2

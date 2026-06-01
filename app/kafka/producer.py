import json
import threading
from typing import Any

from confluent_kafka import KafkaError, Message, Producer

from app.core.config import get_settings
from app.core.logging import get_logger

_logger = get_logger(__name__)
_lock = threading.Lock()
_producer: Producer | None = None


def _delivery_callback(err: KafkaError | None, msg: Message) -> None:
    if err:
        _logger.error("kafka_delivery_failed", error=str(err), topic=msg.topic())
    else:
        _logger.debug(
            "kafka_delivery_success",
            topic=msg.topic(),
            partition=msg.partition(),
            offset=msg.offset(),
        )


def get_producer() -> Producer:
    """Return the shared Producer instance, creating it once (double-checked locking)."""
    global _producer
    if _producer is None:
        with _lock:
            if _producer is None:
                settings = get_settings()
                config: dict[str, Any] = {
                    "bootstrap.servers": settings.kafka_bootstrap_servers,
                    "acks": settings.kafka_producer_acks,
                    "retries": settings.kafka_producer_retries,
                    # Idempotence prevents duplicate messages on producer retry
                    "enable.idempotence": True,
                    # Required by librdkafka when idempotence is on
                    "max.in.flight.requests.per.connection": 5,
                }
                _producer = Producer(config)
                _logger.info(
                    "kafka_producer_initialized",
                    bootstrap_servers=settings.kafka_bootstrap_servers,
                )
    return _producer


def produce(topic: str, value: dict[str, Any], key: str | None = None) -> None:
    """Enqueue a message. Delivery is asynchronous; errors are logged in the callback."""
    producer = get_producer()
    producer.produce(
        topic,
        value=json.dumps(value, default=str).encode("utf-8"),
        key=key.encode("utf-8") if key else None,
        on_delivery=_delivery_callback,
    )
    # poll(0) triggers pending delivery callbacks without blocking the caller
    producer.poll(0)


def flush(timeout: float = 5.0) -> None:
    """Block until all enqueued messages are delivered. Call on graceful shutdown."""
    get_producer().flush(timeout)


def reset_producer() -> None:
    """Tear down the singleton. For use in test teardown only."""
    global _producer
    with _lock:
        _producer = None

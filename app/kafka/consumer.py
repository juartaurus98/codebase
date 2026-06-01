import json
import threading
from typing import Any, Callable

from confluent_kafka import Consumer, KafkaError, Message

from app.core.config import get_settings
from app.core.logging import get_logger
from app.kafka import producer as kafka_producer

_logger = get_logger(__name__)

# Signature for message handlers: receives deserialized dict, returns nothing
MessageHandler = Callable[[dict[str, Any]], None]


class KafkaConsumer:
    """
    Wrapper around confluent_kafka.Consumer with:
    - Manual commit (at-least-once delivery)
    - Per-message retry with configurable max attempts
    - Optional DLQ produce on exhausted retries
    """

    def __init__(
        self,
        topics: list[str],
        group_id: str | None = None,
    ) -> None:
        settings = get_settings()
        config: dict[str, Any] = {
            "bootstrap.servers": settings.kafka_bootstrap_servers,
            "group.id": group_id or settings.kafka_consumer_group_id,
            "auto.offset.reset": "earliest",
            # Disable auto-commit so we control exactly when offset advances
            "enable.auto.commit": False,
        }
        self._consumer = Consumer(config)
        self._consumer.subscribe(topics)
        self._topics = topics
        _logger.info(
            "kafka_consumer_subscribed",
            topics=topics,
            group_id=config["group.id"],
        )

    def consume(
        self,
        handler: MessageHandler,
        stop_event: threading.Event | None = None,
        max_retries: int = 3,
        dlq_topic: str | None = None,
    ) -> None:
        """
        Blocking poll loop. Run in a dedicated thread.
        Set stop_event to trigger a graceful shutdown.
        """
        while not (stop_event and stop_event.is_set()):
            msg: Message | None = self._consumer.poll(timeout=1.0)

            if msg is None:
                continue

            err = msg.error()
            if err:
                if err.code() == KafkaError._PARTITION_EOF:
                    continue
                _logger.error("kafka_consumer_error", error=str(err))
                continue

            self._handle_with_retry(msg, handler, max_retries, dlq_topic)

    def _handle_with_retry(
        self,
        msg: Message,
        handler: MessageHandler,
        max_retries: int,
        dlq_topic: str | None,
    ) -> None:
        raw = msg.value()
        if raw is None:
            _logger.warning("kafka_message_empty", topic=msg.topic())
            self._consumer.commit(asynchronous=False)
            return

        try:
            payload: dict[str, Any] = json.loads(raw)
        except (json.JSONDecodeError, ValueError) as exc:
            _logger.error("kafka_message_deserialize_failed", error=str(exc), topic=msg.topic())
            self._consumer.commit(asynchronous=False)
            return

        last_exc: Exception | None = None
        for attempt in range(1, max_retries + 1):
            try:
                handler(payload)
                # Only commit after the handler succeeds
                self._consumer.commit(asynchronous=False)
                return
            except Exception as exc:
                last_exc = exc
                _logger.warning(
                    "kafka_handler_retry",
                    attempt=attempt,
                    max_retries=max_retries,
                    error=str(exc),
                    topic=msg.topic(),
                )

        # All retries exhausted
        _logger.error(
            "kafka_message_retries_exhausted",
            topic=msg.topic(),
            error=str(last_exc),
        )
        if dlq_topic:
            kafka_producer.produce(dlq_topic, value=payload)
        # Commit to skip the poison message regardless of DLQ
        self._consumer.commit(asynchronous=False)

    def close(self) -> None:
        self._consumer.close()
        _logger.info("kafka_consumer_closed", topics=self._topics)

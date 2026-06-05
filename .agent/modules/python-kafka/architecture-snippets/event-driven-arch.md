# Python Kafka — Event-Driven Architecture Code Patterns

## Event Schema Pattern (Pydantic)

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum

class OrderStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"

# Domain Event
class OrderCreatedEvent(BaseModel):
    """Event emitted when order is created."""
    event_type: str = Field(default="order.created")
    event_id: str  # Unique event ID (UUID)
    aggregate_id: str  # Order ID (partition key)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    customer_id: str
    order_id: str
    total_amount: float
    items: list[dict]  # [{"product_id": "...", "quantity": 2, "price": 50.0}]
    shipping_address: str
    
    class Config:
        use_enum_values = True
    
    def to_json_bytes(self) -> bytes:
        return self.model_dump_json().encode("utf-8")

class OrderShippedEvent(BaseModel):
    """Event emitted when order is shipped."""
    event_type: str = Field(default="order.shipped")
    event_id: str
    aggregate_id: str  # Order ID (partition key)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    order_id: str
    tracking_number: str
    carrier: str
    
    def to_json_bytes(self) -> bytes:
        return self.model_dump_json().encode("utf-8")
```

## Kafka Producer Pattern (Singleton)

```python
from confluent_kafka import Producer
from confluent_kafka.error import KafkaError
import json
import uuid
import structlog
from typing import Optional, Callable
from app.kafka.schemas import OrderCreatedEvent, OrderShippedEvent

logger = structlog.get_logger()

class KafkaProducerManager:
    """Singleton Kafka producer manager (confluent-kafka)."""
    
    _instance: Optional["KafkaProducerManager"] = None
    _producer: Optional[Producer] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def initialize(self, bootstrap_servers: str = "localhost:9092"):
        """Initialize producer (call once on app startup)."""
        if self._producer is None:
            conf = {
                "bootstrap.servers": bootstrap_servers,
                "client.id": "order-service-producer",
                "acks": "all",  # Wait for all in-sync replicas
                "retries": 3,
                "message.send.max.retries": 10
            }
            self._producer = Producer(conf, logger_cb=self._on_logger, error_cb=self._on_error)
            logger.info("kafka_producer_initialized", servers=bootstrap_servers)
    
    def emit_event(self, topic: str, event: BaseModel, partition_key: str, callback: Optional[Callable] = None) -> str:
        """Emit domain event to Kafka topic (non-blocking)."""
        if self._producer is None:
            raise RuntimeError("Producer not initialized. Call initialize() first.")
        
        event_json = event.model_dump_json()
        message_id = str(uuid.uuid4())
        
        def delivery_report(err, msg):
            """Called once for each message produced."""
            if err is not None:
                logger.error(
                    "event_delivery_failed",
                    event_type=event.__class__.__name__,
                    error=str(err)
                )
            else:
                logger.info(
                    "event_emitted",
                    event_type=event.__class__.__name__,
                    topic=msg.topic(),
                    partition=msg.partition(),
                    offset=msg.offset(),
                    message_id=message_id
                )
            
            # Call user callback if provided
            if callback:
                callback(err, msg)
        
        try:
            self._producer.produce(
                topic,
                key=partition_key.encode("utf-8"),
                value=event_json.encode("utf-8"),
                headers=[("message_id", message_id.encode("utf-8"))],
                callback=delivery_report
            )
            # Poll to trigger callbacks
            self._producer.poll(0)
        except BufferError:
            logger.error("kafka_producer_queue_full", topic=topic)
            raise
        
        return message_id
    
    def flush(self, timeout: int = 10):
        """Wait for all messages to be delivered."""
        if self._producer:
            remaining = self._producer.flush(timeout)
            if remaining > 0:
                logger.warning("kafka_messages_not_delivered", count=remaining)
    
    def close(self):
        """Close producer (call on app shutdown)."""
        if self._producer:
            self.flush()
            self._producer = None
            logger.info("kafka_producer_closed")
    
    @staticmethod
    def _on_logger(level, fac, buf):
        """Logger callback."""
        logger.log(level=level, event="kafka_log", message=buf)
    
    @staticmethod
    def _on_error(err):
        """Error callback."""
        logger.error("kafka_producer_error", error=str(err))

# Module-level singleton instance
_producer = KafkaProducerManager()

async def get_producer() -> KafkaProducerManager:
    """Dependency: get Kafka producer."""
    return _producer
```

## Service with Event Emission

```python
from sqlalchemy.orm import Session
from app.kafka.producer import get_producer
from app.kafka.schemas import OrderCreatedEvent, OrderShippedEvent
from app.repositories.base import IRepository
from app.models.orders import Order
import uuid
import structlog

logger = structlog.get_logger()

class OrderService:
    """Business logic for orders (emits events)."""
    
    def __init__(self, repository: IRepository[Order], session: Session):
        self._repository = repository
        self._session = session
        self._producer = get_producer()
    
    def create_order(self, request: CreateOrderRequest) -> OrderResponse:
        """Create order and emit OrderCreatedEvent."""
        
        # Create order entity
        order = Order(
            id=str(uuid.uuid4()),
            customer_id=request.customer_id,
            total_amount=request.total_amount,
            status="PENDING",
            items=request.items,
            shipping_address=request.shipping_address
        )
        
        # Persist (synchronous)
        saved = self._repository.save(order)
        
        # Emit event (after successful save)
        event = OrderCreatedEvent(
            event_id=str(uuid.uuid4()),
            aggregate_id=saved.id,  # Partition key
            customer_id=saved.customer_id,
            order_id=saved.id,
            total_amount=saved.total_amount,
            items=saved.items,
            shipping_address=saved.shipping_address
        )
        
        self._producer.emit_event(
            topic="orders.created",
            event=event,
            partition_key=saved.id  # Ensures all events for same order go to same partition
        )
        
        logger.info("order_created", order_id=saved.id, customer_id=request.customer_id)
        
        return OrderResponse.from_orm(saved)
    
    def ship_order(self, order_id: str, tracking_number: str, carrier: str) -> None:
        """Ship order and emit OrderShippedEvent."""
        
        order = self._repository.get_by_id(order_id)  # Synchronous
        if not order:
            raise ResourceNotFoundError("Order", order_id)
        
        # Update order state
        order.status = "SHIPPED"
        order.tracking_number = tracking_number
        order.carrier = carrier
        
        self._repository.save(order)  # Synchronous
        
        # Emit event
        event = OrderShippedEvent(
            event_id=str(uuid.uuid4()),
            aggregate_id=order.id,
            order_id=order.id,
            tracking_number=tracking_number,
            carrier=carrier
        )
        
        self._producer.emit_event(
            topic="orders.shipped",
            event=event,
            partition_key=order.id
        )
        
        logger.info("order_shipped", order_id=order_id, tracking_number=tracking_number)
```

## Kafka Consumer Pattern

```python
from confluent_kafka import Consumer, Producer, OFFSET_BEGINNING
from confluent_kafka.error import KafkaError
from dataclasses import dataclass, field
from datetime import datetime
import json
from typing import Callable, Dict, Optional
import structlog

logger = structlog.get_logger()


@dataclass
class MessageProcessingResult:
    """Outcome of processing a single Kafka message."""

    success: bool
    event_type: str
    partition: int
    offset: int
    error: Optional[str] = None
    sent_to_dlq: bool = False


class KafkaConsumer:
    """Kafka consumer with message routing to handlers (confluent-kafka)."""

    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        group_id: str = "default",
        dlq_producer: Optional[Producer] = None,
    ):
        self._bootstrap_servers = bootstrap_servers
        self._group_id = group_id
        self._consumer: Optional[Consumer] = None
        self._dlq_producer = dlq_producer
        self._handlers: Dict[str, Callable] = {}
        self._running = False
    
    def register_handler(self, event_type: str, handler: Callable):
        """Register event handler."""
        self._handlers[event_type] = handler
        logger.info("handler_registered", event_type=event_type, handler=handler.__name__)
    
    def start(self, topics: list[str], poll_timeout_ms: int = 1000):
        """Start consuming messages from topics (blocking loop)."""
        conf = {
            "bootstrap.servers": self._bootstrap_servers,
            "group.id": self._group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
            "session.timeout.ms": 6000,
            "logger_cb": self._on_logger,
            "error_cb": self._on_error
        }
        
        self._consumer = Consumer(conf)
        self._consumer.subscribe(topics)
        
        logger.info("kafka_consumer_started", group_id=self._group_id, topics=topics)
        self._running = True
        
        try:
            while self._running:
                msg = self._consumer.poll(timeout=poll_timeout_ms / 1000.0)
                
                if msg is None:
                    continue
                
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        logger.debug("reached_eof", partition=msg.partition())
                    else:
                        logger.error("consumer_error", error=msg.error())
                else:
                    self._process_message(msg)
        
        except KeyboardInterrupt:
            logger.info("consumer_interrupted")
        
        finally:
            self._consumer.close()
            logger.info("kafka_consumer_closed")
    
    def stop(self):
        """Stop consumer loop."""
        self._running = False
    
    def _process_message(self, message) -> "MessageProcessingResult":
        """Process single message with retry + DLQ.

        Always returns a result — never silently swallows errors.
        """
        event_data: dict = {}
        event_type: str = "unknown"

        try:
            event_data = json.loads(message.value().decode("utf-8"))
            event_type = event_data.get("event_type", "unknown")

            if event_type not in self._handlers:
                logger.warning("no_handler_registered", event_type=event_type)
                self._consumer.commit(asynchronous=False)
                return MessageProcessingResult(
                    success=False,
                    event_type=event_type,
                    partition=message.partition(),
                    offset=message.offset(),
                    error="No handler registered for event type",
                    sent_to_dlq=False,
                )

            self._handlers[event_type](event_data)
            self._consumer.commit(asynchronous=False)

            result = MessageProcessingResult(
                success=True,
                event_type=event_type,
                partition=message.partition(),
                offset=message.offset(),
            )
            logger.info(
                "message_processed",
                event_type=event_type,
                partition=result.partition,
                offset=result.offset,
            )
            return result

        except Exception as exc:
            logger.exception(
                "message_processing_failed",
                event_type=event_type,
                error=str(exc),
                partition=message.partition(),
                offset=message.offset(),
            )

            dlq_sent = self._send_to_dlq(message, event_type, exc)
            self._consumer.commit(asynchronous=False)

            return MessageProcessingResult(
                success=False,
                event_type=event_type,
                partition=message.partition(),
                offset=message.offset(),
                error=str(exc),
                sent_to_dlq=dlq_sent,
            )

    def _send_to_dlq(self, message, event_type: str, error: Exception) -> bool:
        """Forward failed message to dead-letter queue topic.

        Returns True if successfully forwarded, False otherwise.
        """
        if self._dlq_producer is None:
            logger.warning("dlq_producer_not_configured", event_type=event_type)
            return False

        dlq_topic = f"{message.topic()}.dlq"
        dlq_payload = {
            "original_topic": message.topic(),
            "original_partition": message.partition(),
            "original_offset": message.offset(),
            "original_message": message.value().decode("utf-8"),
            "event_type": event_type,
            "error_message": str(error),
            "error_type": error.__class__.__name__,
            "timestamp": datetime.utcnow().isoformat(),
        }

        try:
            self._dlq_producer.produce(
                dlq_topic,
                key=message.key(),
                value=json.dumps(dlq_payload).encode("utf-8"),
            )
            self._dlq_producer.poll(0)
            logger.error(
                "message_forwarded_to_dlq",
                dlq_topic=dlq_topic,
                event_type=event_type,
                original_offset=message.offset(),
            )
            return True
        except Exception as dlq_exc:
            logger.exception(
                "dlq_forward_failed",
                dlq_topic=dlq_topic,
                error=str(dlq_exc),
            )
            return False
    
    @staticmethod
    def _on_logger(level, fac, buf):
        """Logger callback."""
        logger.log(level=level, event="kafka_log", message=buf)
    
    @staticmethod
    def _on_error(err):
        """Error callback."""
        logger.error("kafka_consumer_error", error=str(err))
```

## Event Handler Pattern

```python
from dataclasses import dataclass
from typing import Optional
from app.services.order_service import OrderService
import structlog

logger = structlog.get_logger()


@dataclass
class HandlerResult:
    """Outcome of a single event handler invocation."""

    success: bool
    event_type: str
    aggregate_id: str
    message: str
    error: Optional[str] = None


class OrderEventHandlers:
    """Handlers for order domain events."""

    def __init__(self, order_service: OrderService):
        self._order_service = order_service

    def handle_order_created(self, event_data: dict) -> HandlerResult:
        """Handle OrderCreatedEvent — returns result instead of raising."""
        event_type = "order.created"
        order_id = event_data.get("order_id", "unknown")
        try:
            customer_id = event_data["customer_id"]
            total_amount = event_data["total_amount"]

            # Business logic: e.g., send confirmation email, update inventory
            # send_confirmation_email(customer_id, order_id)

            logger.info(
                "order_created_event_received",
                order_id=order_id,
                customer_id=customer_id,
                amount=total_amount,
            )
            return HandlerResult(
                success=True,
                event_type=event_type,
                aggregate_id=order_id,
                message="Order created event processed successfully",
            )

        except KeyError as exc:
            error_msg = f"Missing required field: {exc}"
            logger.error("order_created_handler_failed", order_id=order_id, error=error_msg)
            return HandlerResult(
                success=False,
                event_type=event_type,
                aggregate_id=order_id,
                message="Handler failed due to missing field",
                error=error_msg,
            )
        except Exception as exc:
            logger.exception("order_created_handler_failed", order_id=order_id, error=str(exc))
            return HandlerResult(
                success=False,
                event_type=event_type,
                aggregate_id=order_id,
                message="Handler failed",
                error=str(exc),
            )

    def handle_order_shipped(self, event_data: dict) -> HandlerResult:
        """Handle OrderShippedEvent — returns result instead of raising."""
        event_type = "order.shipped"
        order_id = event_data.get("order_id", "unknown")
        try:
            tracking_number = event_data["tracking_number"]
            carrier = event_data["carrier"]

            # Business logic: e.g., send shipping notification
            # send_shipping_notification(order_id, tracking_number)

            logger.info(
                "order_shipped_event_received",
                order_id=order_id,
                tracking_number=tracking_number,
            )
            return HandlerResult(
                success=True,
                event_type=event_type,
                aggregate_id=order_id,
                message=f"Order shipped via {carrier}, tracking: {tracking_number}",
            )

        except KeyError as exc:
            error_msg = f"Missing required field: {exc}"
            logger.error("order_shipped_handler_failed", order_id=order_id, error=error_msg)
            return HandlerResult(
                success=False,
                event_type=event_type,
                aggregate_id=order_id,
                message="Handler failed due to missing field",
                error=error_msg,
            )
        except Exception as exc:
            logger.exception("order_shipped_handler_failed", order_id=order_id, error=str(exc))
            return HandlerResult(
                success=False,
                event_type=event_type,
                aggregate_id=order_id,
                message="Handler failed",
                error=str(exc),
            )
```

## Consumer Lifespan (Main Entry Point)

```python
from app.kafka.consumer import KafkaConsumer
from app.kafka.handlers import OrderEventHandlers
from app.services.order_service import OrderService
from app.db.session import SessionLocal  # Synchronous session factory
from app.repositories.sql.postgres_order_repository import PostgresOrderRepository
import structlog

logger = structlog.get_logger()

def run_consumer():
    """Run Kafka consumer (long-lived blocking process)."""
    bootstrap_servers = "localhost:9092"

    # Initialize dependencies
    session = SessionLocal()
    try:
        repository = PostgresOrderRepository(session)
        order_service = OrderService(repository, session)
        handlers = OrderEventHandlers(order_service)

        # Dedicated producer for DLQ forwarding
        dlq_producer = build_dlq_producer(bootstrap_servers)

        # Create consumer
        consumer = KafkaConsumer(
            bootstrap_servers=bootstrap_servers,
            group_id="order-processing-group",
            dlq_producer=dlq_producer,
        )

        # Register handlers
        consumer.register_handler("order.created", handlers.handle_order_created)
        consumer.register_handler("order.shipped", handlers.handle_order_shipped)

        # Start consuming (blocks forever)
        consumer.start(topics=["orders.created", "orders.shipped"])
    
    finally:
        session.close()
        logger.info("consumer_session_closed")

if __name__ == "__main__":
    run_consumer()
```

## Testing Event Flow

```python
import pytest
from unittest.mock import MagicMock, patch
from app.services.order_service import OrderService
from app.kafka.schemas import OrderCreatedEvent

def test_create_order_emits_event():
    """Test that creating order emits OrderCreatedEvent to Kafka (synchronous)."""
    
    # Mock dependencies
    mock_repository = MagicMock()
    mock_session = MagicMock()
    mock_producer = MagicMock()
    
    # Create service
    service = OrderService(mock_repository, mock_session)
    service._producer = mock_producer
    
    # Setup mock order
    order_request = CreateOrderRequest(
        customer_id="CUST-123",
        total_amount=100.0,
        items=[{"product_id": "SKU-1", "quantity": 1}],
        shipping_address="123 Main St"
    )
    
    mock_order = Order(id="ORD-123", **order_request.model_dump())
    mock_repository.save.return_value = mock_order
    
    # Execute
    result = service.create_order(order_request)
    
    # Assert: order was saved
    mock_repository.save.assert_called_once()
    
    # Assert: event was emitted to Kafka
    mock_producer.emit_event.assert_called_once()
    call_args = mock_producer.emit_event.call_args
    assert call_args[1]["topic"] == "orders.created"
    assert isinstance(call_args[1]["event"], OrderCreatedEvent)
    assert call_args[1]["partition_key"] == mock_order.id
```

## Error Handling & DLQ Pattern

```python
from confluent_kafka import Producer
from datetime import datetime
from enum import Enum
import json
import structlog

logger = structlog.get_logger()


class ErrorPolicy(Enum):
    """Error handling policies for consumer."""
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    SEND_TO_DLQ = "send_to_dlq"
    SKIP_AND_LOG = "skip_and_log"


def build_dlq_producer(bootstrap_servers: str) -> Producer:
    """Build a dedicated producer for DLQ forwarding."""
    return Producer({"bootstrap.servers": bootstrap_servers, "acks": "all"})


def forward_to_dlq(
    producer: Producer,
    original_topic: str,
    original_key: Optional[bytes],
    message_value: str,
    event_type: str,
    error: Exception,
) -> bool:
    """Forward a failed message to its dead-letter queue topic.

    Returns True if the message was successfully enqueued, False otherwise.
    """
    dlq_topic = f"{original_topic}.dlq"

    dlq_record = {
        "original_topic": original_topic,
        "original_message": message_value,
        "event_type": event_type,
        "error_message": str(error),
        "error_type": error.__class__.__name__,
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        producer.produce(
            dlq_topic,
            key=original_key,
            value=json.dumps(dlq_record).encode("utf-8"),
        )
        producer.poll(0)
        logger.error(
            "message_forwarded_to_dlq",
            dlq_topic=dlq_topic,
            original_topic=original_topic,
            event_type=event_type,
        )
        return True
    except Exception as dlq_exc:
        logger.exception(
            "dlq_forward_failed",
            dlq_topic=dlq_topic,
            error=str(dlq_exc),
        )
        return False
```

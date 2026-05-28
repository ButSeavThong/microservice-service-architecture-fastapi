# app/infrastructure/messaging/broker.py

from faststream.kafka import KafkaBroker
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

broker = KafkaBroker(
    bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
    # ── Consumer group: all replicas of profile-service
    #    share this group → each message is processed by ONE instance.
    #    This is Kafka's horizontal scaling mechanism.
    group_id=settings.KAFKA_CONSUMER_GROUP,

    # ── Reliability settings ──────────────────────────────────
    # acks="all": Producer waits for ALL in-sync Kafka replicas to
    # acknowledge before considering the message "sent".
    # This prevents data loss if a broker crashes mid-write.
    # Tradeoff: slightly higher latency, much higher durability.
)

"""
WHY FastStream over raw aiokafka?

aiokafka gives you raw Kafka bytes. You manually:
- Serialize/deserialize JSON
- Handle consumer group commits
- Wire up error handling
- Integrate with FastAPI lifespan

FastStream gives you:
- Decorator-based consumer registration (@broker.subscriber)
- Automatic Pydantic schema validation on consume
- Automatic serialization on publish
- Built-in FastAPI lifespan integration
- Built-in OpenTelemetry support
- Testing utilities (TestBroker)

This is the same ergonomic leap as going from raw JDBC to Spring Data JPA.
"""
# app/infrastructure/messaging/consumers/identity_consumer.py

from app.core.logger import get_logger
from app.db.session import get_session_context
from app.infrastructure.cache.valkey_client import ProfileCache
from app.infrastructure.messaging.broker import broker
from app.repositories.profile_repository import ProfileRepository
from app.schemas.events.identity_events import IdentityUserCreatedEvent
from app.core.config import settings
from app.services.profile_service import ProfileService

logger = get_logger(__name__)


@broker.subscriber(
    topic=settings.KAFKA_TOPIC_IDENTITY_USER_CREATED,
    group_id=settings.KAFKA_CONSUMER_GROUP,
)
async def handle_identity_user_created(event: IdentityUserCreatedEvent) -> None:
    """
    Consumes `identity.user.created` events from Kafka.

    FastStream automatically:
    - Deserializes the JSON bytes into IdentityUserCreatedEvent
    - Validates the schema via Pydantic
    - Calls this function for each message
    - Commits the Kafka offset after successful processing

    FLOW:
    identity-service publishes → Kafka → THIS FUNCTION → PostgreSQL

    WHY async context manager for session here?
    Kafka consumers run outside FastAPI's request lifecycle.
    There's no HTTP request, no DI system.
    We use get_session_context() to manage our own transaction.

    ERROR HANDLING STRATEGY:
    If this raises an exception:
    - FastStream does NOT commit the Kafka offset
    - The message will be redelivered (at-least-once)
    - Your idempotency check in the service prevents double creation

    This is why idempotency + retry-safety is critical.
    """
    logger.info(
        "identity_user_created_event_received",
        event_id=event.event_id,
        identity_id=event.identity_id,
    )

    async with get_session_context() as session:
        service = ProfileService(
            profile_repo=ProfileRepository(),
            cache=ProfileCache(),
        )
        await service.create_profile_from_identity_event(
            session=session,
            identity_id=event.identity_id,
            email=event.email,
        )
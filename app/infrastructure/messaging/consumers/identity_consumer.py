import json

from app.core.config import settings
from app.core.logger import get_logger
from app.db.session import get_session_context
from app.infrastructure.cache.valkey_client import ProfileCache
from app.infrastructure.messaging.broker import broker
from app.repositories.profile_repository import ProfileRepository
from app.schemas.events.identity_events import IdentityUserCreatedEvent
from app.services.profile_service import ProfileService

logger = get_logger(__name__)

logger.info(
    "consumer_registering",
    topic=settings.KAFKA_TOPIC_IDENTITY_USER_CREATED,
)


@broker.subscriber(
    settings.KAFKA_TOPIC_IDENTITY_USER_CREATED,
    group_id=settings.KAFKA_CONSUMER_GROUP,
    auto_offset_reset="earliest",
)
async def handle_identity_user_created(event):

    try:
        logger.info(
            "raw_kafka_message_received",
            raw_event=str(event),
            event_type=str(type(event)),
        )

        # Kafka bytes -> JSON dict
        if isinstance(event, bytes):
            event = json.loads(event.decode("utf-8"))

        # Validate with Pydantic
        parsed_event = IdentityUserCreatedEvent(**event)

        logger.info(
            "identity_user_created_received",
            event_id=parsed_event.event_id,
            identity_id=parsed_event.identity_id,
            email=parsed_event.email,
        )

        async with get_session_context() as session:

            service = ProfileService(
                profile_repo=ProfileRepository(),
                cache=ProfileCache(),
            )

            await service.create_profile_from_identity_event(
                session=session,
                identity_id=parsed_event.identity_id,
                email=parsed_event.email,
            )

        logger.info(
            "profile_created_successfully",
            identity_id=parsed_event.identity_id,
        )

    except Exception:
        logger.exception("identity_user_created_consumer_failed")
        raise


import asyncio
import json

from aiokafka import AIOKafkaConsumer

from app.core.config import settings
from app.core.logger import get_logger
from app.db.session import get_session_context
from app.infrastructure.cache.valkey_client import ProfileCache
from app.repositories.profile_repository import ProfileRepository
from app.services.profile_service import ProfileService

logger = get_logger(__name__)   # ✅ module-level logger instance


async def consumer_user_created():
    consumer = AIOKafkaConsumer(
        "identity.user.created",
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id=settings.KAFKA_CONSUMER_GROUP,
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        auto_commit_interval_ms=1000,
    )

    await consumer.start()
    logger.info("consumer_started", topic="identity.user.created")

    try:
        async for message in consumer:
            await handle_user_created(consumer, message)   # ✅ pass consumer

    except asyncio.CancelledError:
        logger.info("consumer_cancelled")

    finally:
        await consumer.stop()
        logger.info("consumer_stopped")


async def handle_user_created(consumer: AIOKafkaConsumer, message) -> None:
    try:
        event = json.loads(message.value.decode("utf-8"))

        identity_id = event.get("identity_id")
        email = event.get("email")
        occurred_at = event.get("occurred_at")

        logger.info(
            "user_created_event_received",
            partition=message.partition,
            offset=message.offset,
            identity_id=identity_id,
        )

        profile_repo = ProfileRepository()
        cache = ProfileCache()
        service = ProfileService(profile_repo=profile_repo, cache=cache)

        async with get_session_context() as session:
            profile = await service.create_profile_from_identity_event(
                session=session,
                identity_id=identity_id,
                email=email,
            )

        logger.info(
            "user_created_event_handled",
            profile_id=profile.id,
            identity_id=identity_id,
        )

        await consumer.commit()

    except json.JSONDecodeError as e:
        logger.error("event_decode_failed", error=str(e), raw=message.value)
        await consumer.commit()  # poison pill — skip bad message

    except Exception as e:
        logger.error(
            "user_created_event_failed",
            error=str(e),
            offset=message.offset,
            partition=message.partition,
        )
        # No commit — message redelivered on restart
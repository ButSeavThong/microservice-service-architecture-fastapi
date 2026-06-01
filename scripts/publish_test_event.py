import asyncio
import json
import uuid
from datetime import datetime, timezone

from aiokafka import AIOKafkaProducer
from app.core.config import settings;


async def publish_test_user_created():

    producer = AIOKafkaProducer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS
    )

    await producer.start()

    try:
        event = {
            "event_id": str(uuid.uuid4()),
            "identity_id": "ronaldo",
            "email": "ronaldo@gmail.com",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        }

        await producer.send_and_wait(
            topic="identity.user.created",
            value=json.dumps(event).encode("utf-8"),
        )

        print(f"Published: {event}")

    finally:
        await producer.stop()


asyncio.run(publish_test_user_created())
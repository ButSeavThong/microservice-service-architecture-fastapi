# scripts/publish_test_event.py
# Run this manually to simulate WSO2 publishing a user registration

import asyncio
import json
import uuid
from datetime import datetime, timezone
from aiokafka import AIOKafkaProducer


async def publish_test_user_created():
    producer = AIOKafkaProducer(bootstrap_servers="localhost:9092")
    await producer.start()

    event = {
        "event_id": str(uuid.uuid4()),
        "identity_id": "user-123",
        "email": "thong@gmail.com",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }

    await producer.send_and_wait(
        topic="identity.user.created",
        value=json.dumps(event).encode("utf-8"),
    )

    print(f"Published: {event}")
    await producer.stop()


asyncio.run(publish_test_user_created())
# app/schemas/events/identity_events.py

from datetime import datetime
from pydantic import BaseModel


class IdentityUserCreatedEvent(BaseModel):
    """
    Consumed from topic: identity.user.created
    Published by: WSO2 / identity-service
    """
    event_id: str
    identity_id: str
    email: str
    occurred_at: datetime
# app/schemas/events/profile_events.py

from datetime import datetime
from pydantic import BaseModel


class ProfileCreatedEvent(BaseModel):
    """
    Published to topic: profile.profile.created
    """
    event_id: str
    profile_id: str
    identity_id: str
    email: str
    occurred_at: datetime


class ProfileUpdatedEvent(BaseModel):
    """
    Published to topic: profile.profile.updated
    """
    event_id: str
    profile_id: str
    identity_id: str
    changed_fields: list[str]
    occurred_at: datetime
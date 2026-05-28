# app/schemas/events/identity_events.py

from datetime import datetime
from pydantic import BaseModel, EmailStr


class IdentityUserCreatedEvent(BaseModel):
    """
    Schema for the `identity.user.created` Kafka event.

    This event is published by WSO2 / identity-service when a
    new user registers. We consume it to create an empty profile.

    CRITICAL: This is a CONTRACT between identity-service and
    profile-service. Any change to this schema must be coordinated
    with the publishing team (schema registry / versioning).

    WHY Pydantic for event schemas?
    - Automatic validation on consume: corrupt/malformed events
      raise ValidationError immediately — you know exactly what
      field was wrong, not a generic JSON parse error.
    - Documentation: The schema IS the documentation.
    - Type safety throughout the consumer code.

    event_id: Unique ID for this event occurrence.
    Use it for idempotency — if the same event is delivered twice
    (Kafka at-least-once guarantee), you can detect and skip duplicates.
    """

    event_id: str
    identity_id: str        # WSO2 `sub` claim
    email: str
    occurred_at: datetime


class ProfileCreatedEvent(BaseModel):
    """
    Event we PUBLISH to `profile.profile.created` after creating a profile.

    WHY publish an event after profile creation?
    Other services (notification-service, onboarding-service)
    may need to react to new profiles.

    Event-driven principle: Don't call them directly (tight coupling).
    Publish an event, let interested parties subscribe (loose coupling).
    """

    event_id: str
    profile_id: str
    identity_id: str
    email: str
    occurred_at: datetime


class ProfileUpdatedEvent(BaseModel):
    """
    Published to `profile.profile.updated` after any profile update.

    changed_fields: List of field names that changed.
    Consumers can decide whether to act based on which fields changed.
    E.g., search-service only cares about display_name changes.
    """

    event_id: str
    profile_id: str
    identity_id: str
    changed_fields: list[str]
    occurred_at: datetime
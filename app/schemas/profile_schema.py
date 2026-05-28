# app/schemas/profile_schema.py

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, HttpUrl, field_validator
import re


# ── Base ──────────────────────────────────────────────────────────────────────

class ProfileBase(BaseModel):
    """
    WHY a Base schema?
    We'll have Create, Update, and Response schemas.
    They share common fields. Inheritance avoids repetition.

    This pattern is called "Schema Pyramid":
    ProfileBase → ProfileCreate
    ProfileBase → ProfileUpdate
    ProfileBase → ProfileResponse

    Spring Boot equivalent: This is your DTO base class.
    """
    display_name: str | None = Field(None, max_length=100)
    full_name: str | None = Field(None, max_length=255)
    bio: str | None = Field(None, max_length=500)
    phone_number: str | None = Field(None, max_length=20)
    avatar_url: str | None = Field(None)

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v is None:
            return v
        # Basic E.164 format check
        if not re.match(r"^\+?[1-9]\d{6,14}$", v):
            raise ValueError("Phone number must be in E.164 format, e.g. +6512345678")
        return v


# ── Request Schemas ───────────────────────────────────────────────────────────

class ProfileUpdateRequest(ProfileBase):
    """
    What the client sends when updating their profile.

    WHY no identity_id here?
    The client should NEVER send their own identity_id.
    We extract it from the JWT claims server-side.
    Accepting identity_id from the request body = privilege escalation vulnerability.

    This is a critical security boundary.
    """
    pass


# ── Response Schemas ──────────────────────────────────────────────────────────

class ProfileResponse(ProfileBase):
    """
    What we send back to the client.

    WHY include id and timestamps in responses?
    - id: Clients need it for subsequent requests
    - created_at: Useful for UI ("Member since...")
    - is_onboarded: Frontend needs this to redirect to onboarding flow

    WHY NOT include identity_id in the response?
    It's an internal implementation detail. The client already
    knows their own sub (it's in their JWT). We don't expose
    internal IDs unnecessarily — principle of least exposure.
    """
    id: str
    email: str
    is_active: bool
    is_onboarded: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
    # from_attributes=True allows Pydantic to read from ORM objects
    # (formerly orm_mode=True in Pydantic v1)


class ProfileSummaryResponse(BaseModel):
    """
    Lightweight version for list endpoints or other services
    that need basic profile info without full detail.

    WHY a separate summary schema?
    Returning full profiles in a list endpoint wastes bandwidth
    and leaks unnecessary data. In REST API design, you typically
    have a "list" resource (summary) and "detail" resource (full).
    """
    id: str
    display_name: str | None
    avatar_url: str | None
    is_onboarded: bool

    model_config = {"from_attributes": True}
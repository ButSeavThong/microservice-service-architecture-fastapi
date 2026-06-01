# app/schemas/profile_schema.py

import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class ProfileBase(BaseModel):
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
        if not re.match(r"^\+?[1-9]\d{6,14}$", v):
            raise ValueError("Phone must be E.164 format e.g. +6512345678")
        return v


class ProfileUpdateRequest(ProfileBase):
    pass


class ProfileResponse(ProfileBase):
    id: str
    email: str
    is_active: bool
    is_onboarded: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProfileSummaryResponse(BaseModel):
    id: str
    display_name: str | None
    avatar_url: str | None
    is_onboarded: bool

    model_config = {"from_attributes": True}
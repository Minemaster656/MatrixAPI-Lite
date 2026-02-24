"""
Pydantic schemas for request/response validation.

WHY: Separates API contracts from database models for security and flexibility.
HOW: Uses Pydantic v2 with from_attributes for ORM compatibility.
"""

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def sanitize_url(url: Optional[str]) -> Optional[str]:
    """Sanitize URL to prevent XSS and malicious protocols."""
    if not url:
        return url
    url = url.strip()
    if not url:
        return None
    allowed_schemes = ("http://", "https://", "/")
    if not any(url.lower().startswith(scheme) for scheme in allowed_schemes):
        return None
    if url.lower().startswith("javascript:"):
        return None
    if url.lower().startswith("data:"):
        return None
    return url


def is_safe_static_path(url: Optional[str]) -> bool:
    """Check if URL is a safe static path."""
    if not url:
        return False
    url = url.strip().lower()
    return url.startswith("/static/") or url.startswith("/usr/")
    url = url.strip()
    if not url:
        return None
    allowed_schemes = ("http://", "https://", "/")
    if not any(url.lower().startswith(scheme) for scheme in allowed_schemes):
        return None
    if url.lower().startswith("javascript:"):
        return None
    if url.lower().startswith("data:"):
        return None
    return url


# User schemas


class UserBase(BaseModel):
    """Base user fields shared across schemas."""

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr


class UserCreate(UserBase):
    """Schema for user registration."""

    password: str = Field(..., min_length=6, max_length=100)


class UserLogin(BaseModel):
    """Schema for user login."""

    username: str
    password: str


class UserRead(BaseModel):
    """Schema for user data in responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    email: str
    avatar_url: Optional[str]
    is_active: bool
    is_admin: bool
    created_at: datetime


class UserUpdate(BaseModel):
    """Schema for user updates."""

    avatar_url: Optional[str] = Field(None, max_length=500)

    @field_validator("avatar_url")
    @classmethod
    def validate_avatar_url(cls, v):
        sanitized = sanitize_url(v)
        if sanitized is None and v is not None:
            if not is_safe_static_path(v):
                return None
        return sanitized if sanitized else v


class Token(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Decoded JWT payload."""

    sub: str
    exp: datetime
    iat: datetime


# Character schemas


class CharacterBase(BaseModel):
    """Base character fields."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=2000)


class CharacterCreate(CharacterBase):
    """Schema for character creation."""

    pass


class CharacterUpdate(BaseModel):
    """Schema for character updates."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=2000)
    avatar_url: Optional[str] = Field(None, max_length=500)

    @field_validator("avatar_url")
    @classmethod
    def validate_avatar_url(cls, v):
        sanitized = sanitize_url(v)
        if sanitized is None and v is not None:
            if not is_safe_static_path(v):
                return None
        return sanitized if sanitized else v


class CharacterRead(CharacterBase):
    """Schema for character data in responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    avatar_url: Optional[str]
    created_at: datetime
    updated_at: datetime


# Location schemas


class LocationBase(BaseModel):
    """Base location fields."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=2000)
    background_url: Optional[str] = Field(None, max_length=500)

    @field_validator("background_url")
    @classmethod
    def validate_background_url(cls, v):
        return sanitize_url(v)


class LocationCreate(LocationBase):
    """Schema for location creation."""

    pass


class LocationRead(LocationBase):
    """Schema for location data in responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    creator_id: Optional[str]
    created_at: datetime


# Message schemas


class MessageCreate(BaseModel):
    """Schema for creating a chat message.

    Character is now determined from WebSocket context, not passed explicitly.
    """

    model_config = ConfigDict(from_attributes=True)

    text: str = Field(..., min_length=1, max_length=5000)
    location_id: str
    is_ooc: bool = Field(default=False)


class MessageRead(BaseModel):
    """Schema for message data in responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    character_name: str
    sender_username: Optional[str] = None
    avatar_url: Optional[str] = None
    location_id: str
    is_ooc: bool = Field(default=False)
    ooc_as_user: bool = Field(default=False)
    created_at: datetime

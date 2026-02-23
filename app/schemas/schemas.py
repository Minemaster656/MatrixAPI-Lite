"""
Pydantic schemas for request/response validation.

WHY: Separates API contracts from database models for security and flexibility.
HOW: Uses Pydantic v2 with from_attributes for ORM compatibility.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


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

    id: int
    username: str
    email: str
    avatar_url: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Schema for user updates."""

    avatar_url: Optional[str] = Field(None, max_length=500)


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


class CharacterRead(CharacterBase):
    """Schema for character data in responses."""

    id: int
    owner_id: int
    avatar_url: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Location schemas


class LocationBase(BaseModel):
    """Base location fields."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=2000)
    background_url: Optional[str] = Field(None, max_length=500)


class LocationCreate(LocationBase):
    """Schema for location creation."""

    pass


class LocationRead(LocationBase):
    """Schema for location data in responses."""

    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Message schemas


class MessageCreate(BaseModel):
    """Schema for creating a chat message."""

    text: str = Field(..., min_length=1, max_length=5000)
    character_name: str
    location_id: int


class MessageRead(BaseModel):
    """Schema for message data in responses."""

    id: int
    text: str
    character_name: str
    location_id: int
    created_at: datetime

    class Config:
        from_attributes = True

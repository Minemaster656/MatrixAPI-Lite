"""
Database models for the MatrixAPI application.

WHY: Defines the schema for all persistent data entities.
HOW: Uses SQLModel for ORM with Pydantic validation support.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel, Index


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


class User(SQLModel, table=True):
    """
    User account model.

    WHY: Stores authentication data and user profile information.
    HOW: Username/email unique constraints, hashed password storage.
    """

    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_username", "username", unique=True),
        Index("ix_users_email", "email", unique=True),
    )

    id: Optional[str] = Field(default_factory=generate_uuid, primary_key=True)
    username: str = Field(max_length=50)
    email: str = Field(max_length=255)
    hashed_password: str
    avatar_url: Optional[str] = Field(default=None, max_length=500)
    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: Optional[datetime] = Field(default=None)


class Character(SQLModel, table=True):
    """
    Player character model.

    WHY: Represents a playable character owned by a user.
    HOW: Links to user via owner_id, stores character details and avatar.
    """

    __tablename__ = "characters"
    __table_args__ = (
        Index("ix_characters_name", "name"),
        Index("ix_characters_owner_id", "owner_id"),
    )

    id: Optional[str] = Field(default_factory=generate_uuid, primary_key=True)
    name: str = Field(max_length=100)
    description: str = Field(default="", max_length=2000)
    owner_id: str = Field(foreign_key="users.id")
    avatar_url: Optional[str] = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: Optional[datetime] = Field(default=None)


class Location(SQLModel, table=True):
    """
    Game location model.

    WHY: Defines playable areas in the game world.
    HOW: Stores location metadata with optional background image.
    """

    __tablename__ = "locations"
    __table_args__ = (Index("ix_locations_name", "name"),)

    id: Optional[str] = Field(default_factory=generate_uuid, primary_key=True)
    name: str = Field(max_length=100)
    description: str = Field(default="", max_length=2000)
    background_url: Optional[str] = Field(default=None, max_length=500)
    creator_id: Optional[str] = Field(default=None, foreign_key="users.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: Optional[datetime] = Field(default=None)

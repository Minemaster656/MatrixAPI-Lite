"""
Database models for the MatrixAPI application.

WHY: Defines the schema for all persistent data entities.
HOW: Uses SQLModel for ORM with Pydantic validation support.
"""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """
    User account model.

    WHY: Stores authentication data and user profile information.
    HOW: Username/email unique constraints, hashed password storage.
    """

    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True, max_length=50)
    email: str = Field(unique=True, index=True, max_length=255)
    hashed_password: str
    avatar_url: Optional[str] = Field(default=None, max_length=500)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Character(SQLModel, table=True):
    """
    Player character model.

    WHY: Represents a playable character owned by a user.
    HOW: Links to user via owner_id, stores character details and avatar.
    """

    __tablename__ = "characters"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, max_length=100)
    description: str = Field(default="", max_length=2000)
    owner_id: int = Field(foreign_key="users.id", index=True)
    avatar_url: Optional[str] = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Location(SQLModel, table=True):
    """
    Game location model.

    WHY: Defines playable areas in the game world.
    HOW: Stores location metadata with optional background image.
    """

    __tablename__ = "locations"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, max_length=100)
    description: str = Field(default="", max_length=2000)
    background_url: Optional[str] = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow)

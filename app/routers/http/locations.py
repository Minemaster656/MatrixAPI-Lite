"""
HTTP API endpoints for locations, characters and messages.

WHY: Provides REST API for managing game entities and retrieving data.
HOW: Uses FastAPI router with SQLModel for database operations.
"""

from fastapi import APIRouter, HTTPException
from typing import List
from sqlmodel import select, Session

from app.core.db import engine
from app.models.models import Location, Character
from app.schemas.schemas import (
    LocationCreate,
    LocationRead,
    CharacterCreate,
    CharacterRead,
    MessageCreate,
    MessageRead,
)
from app.services.message_store import message_store

router = APIRouter(prefix="/api", tags=["api"])


@router.post(
    "/locations",
    response_model=LocationRead,
    summary="Create a new location",
    description="Creates a new game location with name, description and optional background URL.",
)
def create_location(location: LocationCreate) -> Location:
    """
    Create a new location in the game world.

    WHY: Allows administrators or game masters to add new playable areas.
    HOW: Validates input via Pydantic, persists to database via SQLModel.

    Args:
        location: LocationCreate schema with name, description and background_url.

    Returns:
        Location: The created location with assigned ID.

    Raises:
        ValidationError: If input data is invalid.
    """
    with Session(engine) as session:
        db_location = Location.model_validate(location)
        session.add(db_location)
        session.commit()
        session.refresh(db_location)
        return db_location


@router.get(
    "/locations",
    response_model=List[LocationRead],
    summary="Get all locations",
    description="Returns a list of all available game locations.",
)
def get_locations() -> List[Location]:
    """
    Retrieve all game locations.

    WHY: Client needs to display available locations for user selection.
    HOW: Simple SELECT query returning all location records.

    Returns:
        List[Location]: All locations in the database.
    """
    with Session(engine) as session:
        return session.exec(select(Location)).all()


@router.get(
    "/locations/{location_id}",
    response_model=LocationRead,
    summary="Get a specific location",
    description="Returns detailed information about a specific location by ID.",
)
def get_location(location_id: int) -> Location:
    """
    Retrieve a single location by ID.

    WHY: Client needs location details including background URL for rendering.
    HOW: Primary key lookup with 404 error if not found.

    Args:
        location_id: The unique identifier of the location.

    Returns:
        Location: The requested location.

    Raises:
        HTTPException: 404 if location not found.
    """
    with Session(engine) as session:
        location = session.get(Location, location_id)
        if not location:
            raise HTTPException(status_code=404, detail="Location not found")
        return location


@router.post(
    "/characters",
    response_model=CharacterRead,
    summary="Create a new character",
    description="Creates a new character with name and optional description.",
)
def create_character(character: CharacterCreate) -> Character:
    """
    Create a new player character.

    WHY: Players need to create characters for role-playing sessions.
    HOW: Validates input and persists character to database.

    Args:
        character: CharacterCreate schema with character details.

    Returns:
        Character: The created character with assigned ID.
    """
    with Session(engine) as session:
        db_character = Character.model_validate(character)
        session.add(db_character)
        session.commit()
        session.refresh(db_character)
        return db_character


@router.get(
    "/characters",
    response_model=List[CharacterRead],
    summary="Get all characters",
    description="Returns a list of all registered characters.",
)
def get_characters() -> List[Character]:
    """
    Retrieve all characters.

    WHY: Admin or debug endpoint to list all registered characters.
    HOW: Simple SELECT query returning all character records.

    Returns:
        List[Character]: All characters in the database.
    """
    with Session(engine) as session:
        return session.exec(select(Character)).all()


@router.get(
    "/locations/{location_id}/messages",
    response_model=List[MessageRead],
    summary="Get messages for a location",
    description="Returns recent messages from a specific location chat.",
)
def get_messages(location_id: int, limit: int = 100) -> List:
    """
    Retrieve messages for a location.

    WHY: Client needs to load chat history when joining a location.
    HOW: Queries message store for recent messages in the location.

    Args:
        location_id: The location to get messages from.
        limit: Maximum number of messages to return (default 100).

    Returns:
        List of messages with character names and timestamps.
    """
    return message_store.get_messages(location_id, limit)

"""
HTTP API endpoints for locations and messages.

WHY: Provides REST API for managing locations and retrieving chat history.
HOW: Uses FastAPI router with SQLModel for database operations.
"""

from typing import List

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select

from app.core.db import engine
from app.models.models import Location
from app.schemas.schemas import (
    LocationCreate,
    LocationRead,
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
        return list(session.exec(select(Location)).all())


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

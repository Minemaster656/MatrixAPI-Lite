"""
Character management API endpoints.

WHY: Provides CRUD operations for user-owned characters.
HOW: Uses JWT authentication to identify character owner.
"""

from datetime import datetime, timezone
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.routers.auth import get_current_user
from app.core.db import engine
from app.models.models import Character, User
from app.schemas.schemas import CharacterCreate, CharacterRead, CharacterUpdate

router = APIRouter(prefix="/api/characters", tags=["characters"])

BUILTIN_AVATARS = [
    "/static/assets/img/builtin_avatars/mtrx_avatar_default1.png",
    "/static/assets/img/builtin_avatars/mtrx_avatar_default2.png",
    "/static/assets/img/builtin_avatars/mtrx_avatar_default3.png",
    "/static/assets/img/builtin_avatars/mtrx_avatar_default4.png",
]


def get_default_avatar(character_name: str) -> str:
    """
    Generate a default avatar based on character name.

    WHY: Provides visual identity for characters without custom avatars.
    HOW: Uses name hash to deterministically select from builtin avatars.

    Args:
        character_name: The character's name for hash generation.

    Returns:
        str: Path to the selected default avatar.
    """
    avatar_index = hash(character_name) % len(BUILTIN_AVATARS)
    return BUILTIN_AVATARS[avatar_index]


@router.post(
    "/",
    response_model=CharacterRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new character",
)
def create_character(
    character_data: CharacterCreate,
    user: Annotated[User, Depends(get_current_user)],
) -> Character:
    """
    Create a new character for the authenticated user.

    WHY: Allows players to create characters for role-playing.
    HOW: Associates character with current user, assigns default avatar.

    Args:
        character_data: Character name and optional description.
        user: The authenticated user from JWT.

    Returns:
        Character: The created character.
    """
    with Session(engine) as session:
        owner_id: str = user.id  # type: ignore
        character = Character(
            name=character_data.name,
            description=character_data.description,
            owner_id=owner_id,
            avatar_url=get_default_avatar(character_data.name),
        )
        session.add(character)
        session.commit()
        session.refresh(character)
        return character


@router.get(
    "/",
    response_model=List[CharacterRead],
    summary="Get user's characters",
)
def get_my_characters(
    user: Annotated[User, Depends(get_current_user)],
) -> List[Character]:
    """
    Get all characters owned by the authenticated user.

    WHY: Displays character list on dashboard/profile page.
    HOW: Filters characters by owner_id from JWT.

    Args:
        user: The authenticated user from JWT.

    Returns:
        List[Character]: User's characters.
    """
    with Session(engine) as session:
        characters = session.exec(
            select(Character).where(Character.owner_id == user.id)
        ).all()
        return list(characters)


@router.get(
    "/{character_id}",
    response_model=CharacterRead,
    summary="Get a specific character",
)
def get_character(
    character_id: str,
    user: Annotated[User, Depends(get_current_user)],
) -> Character:
    """
    Get a specific character by ID.

    WHY: View character details for editing or display.
    HOW: Validates ownership before returning character data.

    Args:
        character_id: The character's unique ID.
        user: The authenticated user from JWT.

    Returns:
        Character: The requested character.

    Raises:
        HTTPException: 404 if not found or not owned by user.
    """
    with Session(engine) as session:
        character = session.get(Character, character_id)
        if not character or character.owner_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Character not found",
            )
        return character


@router.patch(
    "/{character_id}",
    response_model=CharacterRead,
    summary="Update a character",
)
def update_character(
    character_id: str,
    update_data: CharacterUpdate,
    user: Annotated[User, Depends(get_current_user)],
) -> Character:
    """
    Update a character's details.

    WHY: Allows editing character name, description, and avatar.
    HOW: Partial update of provided fields, validates ownership.

    Args:
        character_id: The character's unique ID.
        update_data: Fields to update (partial).
        user: The authenticated user from JWT.

    Returns:
        Character: The updated character.

    Raises:
        HTTPException: 404 if not found or not owned by user.
    """
    with Session(engine) as session:
        character = session.get(Character, character_id)
        if not character or character.owner_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Character not found",
            )

        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(character, key, value)

        character.updated_at = datetime.now(timezone.utc)
        session.add(character)
        session.commit()
        session.refresh(character)
        return character


@router.delete(
    "/{character_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a character",
)
def delete_character(
    character_id: str,
    user: Annotated[User, Depends(get_current_user)],
) -> None:
    """
    Delete a character.

    WHY: Allows users to remove unwanted characters.
    HOW: Validates ownership, then deletes from database.

    Args:
        character_id: The character's unique ID.
        user: The authenticated user from JWT.

    Raises:
        HTTPException: 404 if not found or not owned by user.
    """
    with Session(engine) as session:
        character = session.get(Character, character_id)
        if not character or character.owner_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Character not found",
            )
        session.delete(character)
        session.commit()

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


@router.post("/locations", response_model=LocationRead)
def create_location(location: LocationCreate):
    with Session(engine) as session:
        db_location = Location.model_validate(location)
        session.add(db_location)
        session.commit()
        session.refresh(db_location)
        return db_location


@router.get("/locations", response_model=List[LocationRead])
def get_locations():
    with Session(engine) as session:
        return session.exec(select(Location)).all()


@router.get("/locations/{location_id}", response_model=LocationRead)
def get_location(location_id: int):
    with Session(engine) as session:
        location = session.get(Location, location_id)
        if not location:
            raise HTTPException(status_code=404, detail="Location not found")
        return location


@router.post("/characters", response_model=CharacterRead)
def create_character(character: CharacterCreate):
    with Session(engine) as session:
        db_character = Character.model_validate(character)
        session.add(db_character)
        session.commit()
        session.refresh(db_character)
        return db_character


@router.get("/characters", response_model=List[CharacterRead])
def get_characters():
    with Session(engine) as session:
        return session.exec(select(Character)).all()


@router.get("/locations/{location_id}/messages", response_model=List[MessageRead])
def get_messages(location_id: int, limit: int = 100):
    return message_store.get_messages(location_id, limit)

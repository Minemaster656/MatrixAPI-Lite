from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class LocationBase(BaseModel):
    name: str
    description: str = ""
    background_url: Optional[str] = None


class LocationCreate(LocationBase):
    pass


class LocationRead(LocationBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class CharacterBase(BaseModel):
    name: str
    description: str = ""


class CharacterCreate(CharacterBase):
    owner_id: Optional[int] = None


class CharacterRead(CharacterBase):
    id: int
    owner_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    text: str
    character_name: str
    location_id: int


class MessageRead(BaseModel):
    id: int
    text: str
    character_name: str
    location_id: int
    created_at: datetime

import os
from sqlmodel import SQLModel, create_engine, Session

TESTING = os.getenv("TESTING", "false").lower() == "true"

if TESTING:
    engine = create_engine(
        "sqlite:///test_db.sqlite3", connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine("sqlite:///db.sqlite3")

from app.models.models import Location, Character

if not TESTING:
    SQLModel.metadata.create_all(engine)

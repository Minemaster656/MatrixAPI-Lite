from sqlmodel import SQLModel, create_engine, Session

engine = create_engine("sqlite:///db.sqlite3")

from app.models.models import Location, Character

SQLModel.metadata.create_all(engine)

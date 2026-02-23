"""
Pytest configuration for tests.

Provides:
- Test database (SQLite file)
- Fixtures for database session cleanup
"""

import os
from pathlib import Path
import sys

os.environ["TESTING"] = "true"

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from sqlmodel import SQLModel, Session, delete

from app.core import db as db_module


@pytest.fixture(scope="function", autouse=True)
def setup_db():
    """Create tables before each test and clean up after."""
    from app.models import models

    SQLModel.metadata.create_all(db_module.engine)

    yield

    with Session(db_module.engine) as session:
        session.exec(delete(models.Character))
        session.exec(delete(models.Location))
        session.exec(delete(models.User))
        session.commit()

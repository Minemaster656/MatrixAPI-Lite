"""
Unified location service combining file-based and database content.

WHY: Provides single interface for location data with priority: builtin > instance > database.
HOW: Uses ContentLoader for file-based content, falls back to DB model for legacy data.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from sqlmodel import Session, select

from app.core.db import engine
from app.models.models import Location
from app.services.content_loader import (
    ContentLoader,
    FileLocation,
    content_loader,
)

logger = logging.getLogger(__name__)


class UnifiedLocationService:
    """
    Unified location service with file-first priority.

    Priority order:
    1. content/builtin/ - Built-in read-only locations
    2. content/instances/ - Instance-specific customizations
    3. Database - Legacy fallback

    This allows data-driven content to override database while maintaining
    backward compatibility with existing systems.
    """

    def __init__(self, content_loader: Optional[ContentLoader] = None):
        """
        Initialize unified location service.

        Args:
            content_loader: Optional custom content loader (uses singleton if None)
        """
        from app.services.content_loader import content_loader as _content_loader

        self._content_loader = content_loader or _content_loader

    def _load_from_db(self, location_id: Optional[str] = None) -> List[Location]:
        """
        Load locations from database (legacy fallback).

        Args:
            location_id: Optional ID to load single location

        Returns:
            List of Location objects from database
        """
        with Session(engine) as session:
            if location_id:
                location = session.get(Location, location_id)
                return [location] if location else []
            return list(session.exec(select(Location)).all())

    def _location_to_dict(self, location: Location) -> Dict:
        """
        Convert database Location to dict format.

        Args:
            location: Database Location model

        Returns:
            Dict compatible with FileLocation structure
        """
        return {
            "id": location.id,
            "name": location.name,
            "description": location.description,
            "type": "location",
            "background_url": location.background_url,
            "created_at": location.created_at.isoformat()
            if location.created_at
            else None,
            "source": "database",
        }

    def get_all_locations(self) -> List[Dict]:
        """
        Get all locations with file content taking priority over database.

        Returns:
            List of location dicts (file-based first, then database legacy)
        """
        file_locations = self._content_loader.get_all_locations()

        result = []
        seen_names = set()

        for loc in file_locations:
            result.append(loc.model_dump())
            seen_names.add(loc.name.lower())

        db_locations = self._load_from_db()
        for db_loc in db_locations:
            if db_loc.name.lower() not in seen_names:
                result.append(self._location_to_dict(db_loc))

        return result

    def get_location_by_name(self, name: str) -> Optional[Dict]:
        """
        Get location by name (file content takes priority).

        Args:
            name: Location name (case-insensitive)

        Returns:
            Location dict or None if not found
        """
        file_location = self._content_loader.get_location(name)
        if file_location:
            return file_location.model_dump()

        with Session(engine) as session:
            db_location = session.exec(
                select(Location).where(Location.name.ilike(name))
            ).first()
            if db_location:
                return self._location_to_dict(db_location)

        return None

    def get_location_by_id(self, location_id: str) -> Optional[Dict]:
        """
        Get location by ID (checks file content first, then database).

        Args:
            location_id: Location UUID

        Returns:
            Location dict or None if not found
        """
        for loc in self._content_loader.get_all_locations():
            if loc.id == location_id:
                return loc.model_dump()

        db_location = self._load_from_db(location_id)
        if db_location:
            return self._location_to_dict(db_location[0])

        return None

    def list_location_names(self) -> List[str]:
        """
        Get all location names from files and database.

        Returns:
            List of unique location names
        """
        names = set(self._content_loader.list_location_names())

        for loc in self._load_from_db():
            names.add(loc.name.lower())

        return sorted(list(names))

    def location_exists(self, name: str) -> bool:
        """
        Check if location exists in files or database.

        Args:
            name: Location name

        Returns:
            True if location exists
        """
        if self._content_loader.location_exists(name):
            return True

        with Session(engine) as session:
            return (
                session.exec(select(Location).where(Location.name.ilike(name))).first()
                is not None
            )

    def is_builtin_location(self, name: str) -> bool:
        """
        Check if location is from builtin content.

        Args:
            name: Location name

        Returns:
            True if location is from builtin
        """
        loc = self._content_loader.get_location(name)
        if not loc:
            return False
        return loc.instance_data is None

    def is_instance_location(self, name: str) -> bool:
        """
        Check if location is an instance override.

        Args:
            name: Location name

        Returns:
            True if location is from instances
        """
        return self._content_loader.is_instance_location(name)

    def get_location_source(self, name: str) -> str:
        """
        Get the source of a location (builtin/instance/database).

        Args:
            name: Location name

        Returns:
            Source type string
        """
        if self._content_loader.is_instance_location(name):
            return "instance"
        if self._content_loader.location_exists(name):
            return "builtin"
        if self.location_exists(name):
            return "database"
        return "not_found"


unified_location_service = UnifiedLocationService()

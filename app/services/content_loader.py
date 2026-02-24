"""
Content loader service for data-driven game content.

WHY: Implements priority-based content loading: builtin > instance > database.
HOW: Loads location data from JSON files in content/builtin and content/instances,
     falling back to database for legacy data. Supports hot-reloading and caching.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)


class LocationProperties(BaseModel):
    """Location properties configuration."""

    max_players: int = Field(default=50, ge=1, le=1000)
    is_public: bool = True
    is_active: bool = True
    allow_combat: bool = True
    allow_trading: bool = True
    allow_chat: bool = True
    background_url: Optional[str] = None
    gravity: Optional[str] = None
    atmosphere: Optional[str] = None


class LocationMetadata(BaseModel):
    """Location metadata."""

    author: str = "system"
    version: str = "1.0.0"
    tags: List[str] = []
    difficulty: str = "medium"
    source: Optional[str] = None
    instance_created: Optional[str] = None


class LocationContent(BaseModel):
    """Location descriptive content."""

    description: str = ""
    atmosphere: str = ""
    weather: str = ""
    terrain: str = ""
    resources: List[str] = []
    npcs: List[str] = []
    events: List[str] = []


class InstanceData(BaseModel):
    """Instance-specific data for customization."""

    owner: str = "current_instance"
    customizations: Dict = {}
    modifications: List[str] = []


class FileLocation(BaseModel):
    """
    File-based location model.

    Represents a location loaded from JSON file (builtin or instance).
    """

    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=100)
    type: str = Field(default="location")
    description: str = Field(default="", max_length=2000)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    parent: Optional[str] = None
    children: List[str] = []
    properties: LocationProperties = Field(default_factory=LocationProperties)
    metadata: LocationMetadata = Field(default_factory=LocationMetadata)
    content: LocationContent = Field(default_factory=LocationContent)
    exits: Dict[str, str] = {}
    connections: List[str] = []
    instance_data: Optional[InstanceData] = None

    def to_db_format(self) -> Dict:
        """
        Convert to database-compatible format for backward compatibility.

        Returns:
            Dict with fields matching Location DB model.
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.content.description or self.description,
            "background_url": self.properties.background_url,
            "created_at": self.created_at or datetime.now().isoformat(),
        }


class ContentLoader:
    """
    Loads and manages game content with priority: builtin > instance > database.

    Content loading order:
    1. content/builtin/ - Read-only built-in content
    2. content/instances/ - Instance-specific overrides/customizations
    3. Database - Legacy fallback for backward compatibility

    Security: All paths are validated to prevent directory traversal attacks.
    """

    SUPPORTED_TYPES = {"planet", "space", "location", "sublocation"}
    ALLOWED_FILENAME_PATTERN = r"^[a-zA-Z0-9_\-\u0400-\u04FF]+\.json$"

    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize content loader.

        Args:
            base_path: Base directory for content (defaults to ./content)
        """
        self._base_path = base_path or Path(".")
        self._builtin_path = self._base_path / "builtin" / "locations"
        self._instance_path = self._base_path / "instance_content" / "locations"
        self._cache: Dict[str, FileLocation] = {}
        self._cache_enabled = True

    def _validate_path(self, path: Path, base: Path) -> Path:
        """
        Validate path to prevent directory traversal.

        Args:
            path: Path to validate
            base: Base directory path

        Returns:
            Validated absolute path

        Raises:
            ValueError: If path attempts directory traversal
        """
        resolved = path.resolve()
        base_resolved = base.resolve()
        if not str(resolved).startswith(str(base_resolved)):
            raise ValueError(f"Path traversal attempt detected: {path}")
        return resolved

    def _load_json_file(self, file_path: Path) -> Optional[Dict]:
        """
        Safely load and parse JSON file.

        Args:
            file_path: Path to JSON file

        Returns:
            Parsed JSON dict or None if file doesn't exist
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {file_path}: {e}")
            return None

    def _load_location_from_file(self, file_path: Path) -> Optional[FileLocation]:
        """
        Load location from JSON file with validation.

        Args:
            file_path: Path to location JSON file

        Returns:
            FileLocation object or None if invalid
        """
        data = self._load_json_file(file_path)
        if data is None:
            return None

        try:
            return FileLocation(**data)
        except ValidationError as e:
            logger.error(f"Validation error in {file_path}: {e}")
            return None

    def _scan_directory(self, directory: Path) -> Dict[str, FileLocation]:
        """
        Scan directory for location JSON files.

        Args:
            directory: Directory to scan

        Returns:
            Dict mapping location name to FileLocation
        """
        locations: Dict[str, FileLocation] = {}

        if not directory.exists():
            return locations

        for file_path in directory.glob("*.json"):
            validated = self._validate_path(file_path, directory)
            location = self._load_location_from_file(validated)
            if location:
                key = location.name.lower()
                locations[key] = location
                logger.debug(f"Loaded location: {location.name} from {file_path}")

        return locations

    def _load_all_locations(self) -> Dict[str, FileLocation]:
        """
        Load all locations from builtin and instance directories.

        Returns:
            Dict mapping location name (lowercase) to FileLocation
        """
        all_locations: Dict[str, FileLocation] = {}

        builtin_locations = self._scan_directory(self._builtin_path)
        all_locations.update(builtin_locations)

        instance_locations = self._scan_directory(self._instance_path)
        for name, location in instance_locations.items():
            if name in all_locations:
                logger.info(f"Instance location '{location.name}' overrides builtin")
            all_locations[name] = location

        return all_locations

    def get_location(self, name: str) -> Optional[FileLocation]:
        """
        Get location by name with priority: instance > builtin.

        Args:
            name: Location name (case-insensitive)

        Returns:
            FileLocation or None if not found
        """
        import re

        key = name.lower()

        if not re.match(self.ALLOWED_FILENAME_PATTERN, f"{key}.json"):
            logger.warning(
                f"Invalid location name format (potential path traversal): {name}"
            )
            return None

        if self._cache_enabled and key in self._cache:
            return self._cache[key]

        locations = self._load_all_locations()
        location = locations.get(key)

        if location and self._cache_enabled:
            self._cache[key] = location

        return location

    def get_all_locations(self) -> List[FileLocation]:
        """
        Get all available locations (builtin + instance).

        Returns:
            List of all FileLocation objects
        """
        return list(self._load_all_locations().values())

    def list_location_names(self) -> List[str]:
        """
        Get list of all available location names.

        Returns:
            List of location names
        """
        return list(self._load_all_locations().keys())

    def location_exists(self, name: str) -> bool:
        """
        Check if location exists in files.

        Args:
            name: Location name

        Returns:
            True if location exists
        """
        return self.get_location(name) is not None

    def is_instance_location(self, name: str) -> bool:
        """
        Check if location is an instance override.

        Args:
            name: Location name

        Returns:
            True if location is from instances directory
        """
        location = self.get_location(name)
        if not location:
            return False

        if location.instance_data is not None:
            return True

        return False

    def invalidate_cache(self) -> None:
        """Clear the content cache to force reload."""
        self._cache.clear()
        logger.info("Content cache invalidated")

    def enable_cache(self) -> bool:
        """Enable caching. Returns previous state."""
        old = self._cache_enabled
        self._cache_enabled = True
        return old

    def disable_cache(self) -> bool:
        """Disable caching. Returns previous state."""
        old = self._cache_enabled
        self._cache_enabled = False
        self._cache.clear()
        return old


content_loader = ContentLoader(Path("."))

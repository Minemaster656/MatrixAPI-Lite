"""
Tests for content loader service.

Tests the priority-based content loading: builtin > instance > database.
"""

import json
import tempfile
from pathlib import Path

import pytest

from app.services.content_loader import (
    ContentLoader,
    FileLocation,
    LocationProperties,
    LocationMetadata,
    LocationContent,
    InstanceData,
)


@pytest.fixture
def temp_content_dir(tmp_path):
    """Create temporary content directory with builtin and instance_content."""
    # ContentLoader expects base_path, then appends builtin/locations and instance_content/locations
    # So we just create the base directories
    base_builtin = tmp_path / "builtin" / "locations"
    base_instance = tmp_path / "instance_content" / "locations"
    base_builtin.mkdir(parents=True)
    base_instance.mkdir(parents=True)
    return tmp_path


@pytest.fixture
def sample_builtin_location():
    """Sample builtin location data."""
    return {
        "name": "Таверна",
        "type": "location",
        "description": "Уютное место для отдыха",
        "properties": {
            "max_players": 50,
            "is_public": True,
        },
        "metadata": {
            "author": "system",
            "version": "1.0.0",
        },
    }


@pytest.fixture
def sample_instance_location():
    """Sample instance location data."""
    return {
        "name": "Таверна",
        "type": "location",
        "description": "Кастомная таверна",
        "instance_data": {
            "owner": "player1",
            "customizations": {"custom_flag": True},
        },
    }


class TestContentLoader:
    """Tests for ContentLoader class."""

    def test_load_builtin_location(self, temp_content_dir, sample_builtin_location):
        """Test loading location from builtin directory."""
        builtin_path = temp_content_dir / "builtin" / "locations"
        location_file = builtin_path / "tavern.json"

        with open(location_file, "w", encoding="utf-8") as f:
            json.dump(sample_builtin_location, f)

        loader = ContentLoader(temp_content_dir)
        location = loader.get_location("Таверна")

        assert location is not None
        assert location.name == "Таверна"
        assert location.type == "location"

    def test_location_case_insensitive(self, temp_content_dir, sample_builtin_location):
        """Test that location lookup is case-insensitive."""
        builtin_path = temp_content_dir / "builtin" / "locations"
        location_file = builtin_path / "tavern.json"

        with open(location_file, "w", encoding="utf-8") as f:
            json.dump(sample_builtin_location, f)

        loader = ContentLoader(temp_content_dir)

        assert loader.get_location("ТАВЕРНА") is not None
        assert loader.get_location("таверна") is not None

    def test_instance_overrides_builtin(
        self, temp_content_dir, sample_builtin_location, sample_instance_location
    ):
        """Test that instance locations override builtin."""
        builtin_path = temp_content_dir / "builtin" / "locations"
        instance_path = temp_content_dir / "instance_content" / "locations"

        with open(builtin_path / "tavern.json", "w", encoding="utf-8") as f:
            json.dump(sample_builtin_location, f)

        with open(instance_path / "tavern.json", "w", encoding="utf-8") as f:
            json.dump(sample_instance_location, f)

        loader = ContentLoader(temp_content_dir)
        location = loader.get_location("Таверна")

        assert location is not None
        assert location.instance_data is not None

    def test_location_not_found(self, temp_content_dir):
        """Test that None is returned for non-existent location."""
        loader = ContentLoader(temp_content_dir)
        assert loader.get_location("NonExistent") is None

    def test_get_all_locations(self, temp_content_dir, sample_builtin_location):
        """Test getting all locations."""
        builtin_path = temp_content_dir / "builtin" / "locations"

        with open(builtin_path / "tavern.json", "w", encoding="utf-8") as f:
            json.dump(sample_builtin_location, f)

        with open(builtin_path / "forest.json", "w", encoding="utf-8") as f:
            json.dump({**sample_builtin_location, "name": "Лес"}, f)

        loader = ContentLoader(temp_content_dir)
        locations = loader.get_all_locations()

        assert len(locations) == 2
        names = [loc.name for loc in locations]
        assert "Таверна" in names
        assert "Лес" in names

    def test_path_traversal_prevention(self, temp_content_dir):
        """Test that path traversal attempts are blocked."""
        builtin_path = temp_content_dir / "builtin" / "locations"
        location_file = builtin_path / "tavern.json"

        with open(location_file, "w", encoding="utf-8") as f:
            json.dump({"name": "Test"}, f)

        loader = ContentLoader(temp_content_dir)

        # Path traversal should return None instead of raising to prevent information leakage
        assert loader.get_location("../../../etc/passwd") is None

    def test_invalid_json_handled(self, temp_content_dir):
        """Test that invalid JSON files are handled gracefully."""
        builtin_path = temp_content_dir / "builtin" / "locations"
        location_file = builtin_path / "bad.json"

        with open(location_file, "w", encoding="utf-8") as f:
            f.write("invalid json{{{")

        loader = ContentLoader(temp_content_dir)
        assert loader.get_location("bad") is None

    def test_cache_invalidation(self, temp_content_dir, sample_builtin_location):
        """Test cache can be invalidated."""
        builtin_path = temp_content_dir / "builtin" / "locations"
        location_file = builtin_path / "tavern.json"

        with open(location_file, "w", encoding="utf-8") as f:
            json.dump(sample_builtin_location, f)

        loader = ContentLoader(temp_content_dir)
        loader.enable_cache()

        assert loader.get_location("Таверна") is not None

        loader.invalidate_cache()
        assert loader._cache == {}


class TestFileLocation:
    """Tests for FileLocation model."""

    def test_default_values(self):
        """Test default values are set correctly."""
        location = FileLocation(name="Test")

        assert location.type == "location"
        assert location.properties.max_players == 50
        assert location.metadata.author == "system"

    def test_to_db_format(self):
        """Test conversion to database format."""
        location = FileLocation(
            name="Test",
            id="test-id",
            description="Test desc",
            content=LocationContent(description="Content desc"),
            properties=LocationProperties(background_url="http://example.com/bg.jpg"),
        )

        db_format = location.to_db_format()

        assert db_format["id"] == "test-id"
        assert db_format["name"] == "Test"
        assert db_format["background_url"] == "http://example.com/bg.jpg"

    def test_instance_detection(self):
        """Test instance location detection."""
        builtin_location = FileLocation(name="Test")
        assert builtin_location.instance_data is None

        instance_location = FileLocation(
            name="Test",
            instance_data=InstanceData(owner="player1"),
        )
        assert instance_location.instance_data is not None


class TestContentPriority:
    """Tests for content priority (builtin > instance > database)."""

    def test_builtin_priority_over_instance(
        self, temp_content_dir, sample_builtin_location
    ):
        """Test that instance with same name can override builtin."""
        builtin_path = temp_content_dir / "builtin" / "locations"
        instance_path = temp_content_dir / "instance_content" / "locations"

        with open(builtin_path / "shared.json", "w", encoding="utf-8") as f:
            json.dump({**sample_builtin_location, "name": "Shared"}, f)

        with open(instance_path / "shared.json", "w", encoding="utf-8") as f:
            json.dump(
                {
                    **sample_builtin_location,
                    "name": "Shared",
                    "description": "Instance version",
                },
                f,
            )

        loader = ContentLoader(temp_content_dir)

        location = loader.get_location("Shared")
        assert location is not None

    def test_list_all_location_names(self, temp_content_dir, sample_builtin_location):
        """Test listing all location names."""
        builtin_path = temp_content_dir / "builtin" / "locations"

        with open(builtin_path / "a.json", "w", encoding="utf-8") as f:
            json.dump({**sample_builtin_location, "name": "Alpha"}, f)

        with open(builtin_path / "b.json", "w", encoding="utf-8") as f:
            json.dump({**sample_builtin_location, "name": "Beta"}, f)

        loader = ContentLoader(temp_content_dir)
        names = loader.list_location_names()

        assert len(names) == 2
        assert "alpha" in names
        assert "beta" in names

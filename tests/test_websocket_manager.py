"""
Tests for WebSocket connection manager.

Tests for:
- Connection management
- User info storage
- Broadcasting messages
- Location-based user tracking
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.core.websocket_manager import ConnectionManager, ConnectionInfo, manager


class TestConnectionInfo:
    """Tests for ConnectionInfo dataclass."""

    def test_connection_info_defaults(self):
        """ConnectionInfo should have default values."""
        info = ConnectionInfo("user", None, None, None, None)
        assert info.username == "user"
        assert info.character_name is None
        assert info.character_id is None
        assert info.avatar_url is None
        assert info.location_id is None


class TestConnectionManager:
    """Tests for ConnectionManager class."""

    @pytest.fixture
    def conn_manager(self):
        """Create fresh ConnectionManager instance."""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket."""
        ws = AsyncMock()
        ws.send_text = AsyncMock()
        ws.close = AsyncMock()
        ws.accept = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_connect_creates_connection(self, conn_manager, mock_websocket):
        """Connect should store websocket with default values."""
        await conn_manager.connect(mock_websocket, username="TestUser")
        assert mock_websocket in conn_manager.active_connections

    @pytest.mark.asyncio
    async def test_connect_accepts_websocket(self, conn_manager, mock_websocket):
        """Connect should accept the WebSocket."""
        await conn_manager.connect(mock_websocket, username="TestUser")
        mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_removes_connection(self, conn_manager, mock_websocket):
        """Disconnect should remove websocket from active connections."""
        await conn_manager.connect(mock_websocket, username="TestUser")
        conn_manager.disconnect(mock_websocket)
        assert mock_websocket not in conn_manager.active_connections

    def test_disconnect_nonexistent_raises_no_error(self, conn_manager, mock_websocket):
        """Disconnecting non-existent connection should not raise."""
        conn_manager.disconnect(mock_websocket)

    def test_get_info_existing(self, conn_manager, mock_websocket):
        """Get info should return stored info."""
        conn_manager.active_connections[mock_websocket] = ConnectionInfo(
            username="TestUser",
            character_name="Hero",
            character_id=1,
            avatar_url="/avatar.png",
            location_id=5,
        )
        info = conn_manager.get_info(mock_websocket)
        assert info.username == "TestUser"
        assert info.character_name == "Hero"

    def test_get_info_nonexistent(self, conn_manager, mock_websocket):
        """Get info for unknown websocket should return defaults."""
        info = conn_manager.get_info(mock_websocket)
        assert info.username == "Anonymous"
        assert info.character_name is None

    def test_get_username_returns_character_name(self, conn_manager, mock_websocket):
        """Get username should prefer character name."""
        conn_manager.active_connections[mock_websocket] = ConnectionInfo(
            username="realuser",
            character_name="mychar",
            character_id=None,
            avatar_url=None,
            location_id=None,
        )
        assert conn_manager.get_username(mock_websocket) == "mychar"

    def test_get_username_returns_username(self, conn_manager, mock_websocket):
        """Get username should return username if no character."""
        conn_manager.active_connections[mock_websocket] = ConnectionInfo(
            username="realuser",
            character_name="",
            character_id=None,
            avatar_url=None,
            location_id=None,
        )
        assert conn_manager.get_username(mock_websocket) == "realuser"

    def test_get_username_anonymous_default(self, conn_manager, mock_websocket):
        """Get username should return Anonymous as fallback."""
        info = conn_manager.get_info(mock_websocket)
        assert conn_manager.get_username(mock_websocket) == "Anonymous"

    @pytest.mark.asyncio
    async def test_set_location_updates_location(self, conn_manager, mock_websocket):
        """Set location should update the location_id."""
        await conn_manager.connect(mock_websocket)
        conn_manager.set_location(mock_websocket, 42)
        info = conn_manager.get_info(mock_websocket)
        assert info.location_id == 42

    @pytest.mark.asyncio
    async def test_set_character_updates_info(self, conn_manager, mock_websocket):
        """Set character should update character fields."""
        await conn_manager.connect(mock_websocket)
        conn_manager.set_character(mock_websocket, "Warrior", "/avatar.png", 10)
        info = conn_manager.get_info(mock_websocket)
        assert info.character_name == "Warrior"
        assert info.avatar_url == "/avatar.png"
        assert info.character_id == 10

    @pytest.mark.asyncio
    async def test_set_username_updates_username(self, conn_manager, mock_websocket):
        """Set username should update username field."""
        await conn_manager.connect(mock_websocket)
        conn_manager.set_username(mock_websocket, "NewName")
        info = conn_manager.get_info(mock_websocket)
        assert info.username == "NewName"

    @pytest.mark.asyncio
    async def test_get_users_on_location_returns_correct_users(self, conn_manager):
        """Get users on location should return users in that location."""
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws3 = AsyncMock()

        await conn_manager.connect(ws1, username="user1")
        await conn_manager.connect(ws2, username="user2")
        await conn_manager.connect(ws3, username="user3")

        conn_manager.set_location(ws1, 1)
        conn_manager.set_location(ws2, 1)
        conn_manager.set_location(ws3, 2)

        users_in_loc1 = conn_manager.get_users_on_location(1)
        users_in_loc2 = conn_manager.get_users_on_location(2)

        assert len(users_in_loc1) == 2
        assert len(users_in_loc2) == 1

    def test_find_connection_by_username(self, conn_manager, mock_websocket):
        """Find connection by username should work."""
        conn_manager.active_connections[mock_websocket] = ConnectionInfo(
            username="searchable_user",
            character_name=None,
            character_id=None,
            avatar_url=None,
            location_id=None,
        )
        result = conn_manager.find_connection_by_username("searchable_user")
        assert result is mock_websocket

    def test_find_connection_by_character_name(self, conn_manager, mock_websocket):
        """Find connection should also search by character name."""
        conn_manager.active_connections[mock_websocket] = ConnectionInfo(
            username="real_user",
            character_name="my_character",
            character_id=None,
            avatar_url=None,
            location_id=None,
        )
        result = conn_manager.find_connection_by_username("my_character")
        assert result is mock_websocket

    def test_find_connection_returns_none(self, conn_manager):
        """Find connection should return None if not found."""
        result = conn_manager.find_connection_by_username("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_broadcast_to_all_when_no_location(self, conn_manager):
        """Broadcast without location should send to all."""
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws1.send_text = AsyncMock()
        ws2.send_text = AsyncMock()

        await conn_manager.connect(ws1)
        await conn_manager.connect(ws2)

        await conn_manager.broadcast({"type": "test"})

        ws1.send_text.assert_called_once()
        ws2.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_to_specific_location(self, conn_manager):
        """Broadcast with location should send only to that location."""
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws1.send_text = AsyncMock()
        ws2.send_text = AsyncMock()

        await conn_manager.connect(ws1)
        await conn_manager.connect(ws2)

        conn_manager.set_location(ws1, 1)
        conn_manager.set_location(ws2, 2)

        await conn_manager.broadcast({"type": "test"}, location_id=1)

        ws1.send_text.assert_called_once()
        ws2.send_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_personal(self, conn_manager, mock_websocket):
        """Send personal should send to specific websocket."""
        mock_websocket.send_text = AsyncMock()
        await conn_manager.send_personal({"type": "personal"}, mock_websocket)
        mock_websocket.send_text.assert_called_once()


class TestManagerSingleton:
    """Tests for the manager singleton."""

    def test_manager_is_singleton(self):
        """Manager should be a singleton instance."""
        from app.core.websocket_manager import manager

        assert isinstance(manager, ConnectionManager)

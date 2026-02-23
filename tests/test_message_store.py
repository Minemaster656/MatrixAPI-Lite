"""
Tests for message store service.

Tests for:
- Adding messages
- Retrieving messages
- Message ID generation
- Location-based message storage
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from datetime import datetime
from app.services.message_store import MessageStore
from app.schemas.schemas import MessageCreate


class TestMessageStore:
    """Tests for MessageStore class."""

    @pytest.fixture
    def store(self):
        """Create fresh MessageStore instance."""
        return MessageStore()

    def test_add_message_returns_message(self, store):
        """Add message should return the created message."""
        msg_data = MessageCreate(
            text="Hello world",
            character_name="Hero",
            location_id=1,
        )
        result = store.add_message(msg_data)
        assert result.text == "Hello world"
        assert result.character_name == "Hero"
        assert result.location_id == 1
        assert result.id is not None

    def test_add_message_stores_in_location(self, store):
        """Messages should be stored per location."""
        msg1 = MessageCreate(text="First", character_name="Hero", location_id=1)
        msg2 = MessageCreate(text="Second", character_name="Hero", location_id=1)
        msg3 = MessageCreate(text="Other loc", character_name="Hero", location_id=2)

        store.add_message(msg1)
        store.add_message(msg2)
        store.add_message(msg3)

        loc1_messages = store.get_messages(1)
        loc2_messages = store.get_messages(2)

        assert len(loc1_messages) == 2
        assert len(loc2_messages) == 1

    def test_get_messages_empty_location(self, store):
        """Getting messages for empty location should return empty list."""
        result = store.get_messages(999)
        assert result == []

    def test_get_messages_default_limit(self, store):
        """Default limit should be 100 messages."""
        for i in range(150):
            store.add_message(
                MessageCreate(
                    text=f"Message {i}",
                    character_name="Hero",
                    location_id=1,
                )
            )

        messages = store.get_messages(1)
        assert len(messages) == 100

    def test_get_messages_custom_limit(self, store):
        """Custom limit should work correctly."""
        for i in range(50):
            store.add_message(
                MessageCreate(
                    text=f"Message {i}",
                    character_name="Hero",
                    location_id=1,
                )
            )

        messages = store.get_messages(1, limit=10)
        assert len(messages) == 10

    def test_message_ids_increment(self, store):
        """Message IDs should increment uniquely."""
        msg1 = MessageCreate(text="First", character_name="Hero", location_id=1)
        msg2 = MessageCreate(text="Second", character_name="Hero", location_id=1)

        result1 = store.add_message(msg1)
        result2 = store.add_message(msg2)

        assert result2.id > result1.id

    def test_message_has_created_at(self, store):
        """Messages should have created_at timestamp."""
        msg = MessageCreate(text="Test", character_name="Hero", location_id=1)
        result = store.add_message(msg)
        assert result.created_at is not None

    def test_generate_id_increments(self, store):
        """Generate ID should increment."""
        id1 = store.generate_id()
        id2 = store.generate_id()
        assert id2 > id1


class TestMessageStoreSingleton:
    """Tests for the message_store singleton."""

    def test_message_store_exists(self):
        """Message store singleton should exist."""
        from app.services.message_store import message_store

        assert isinstance(message_store, MessageStore)

import threading
from datetime import datetime, UTC
from typing import Dict, List, Optional, Tuple

from app.schemas.schemas import MessageCreate, MessageRead
from app.core.config import (
    DELETED_USER_DISPLAY_NAME,
    DELETED_CHARACTER_DISPLAY_NAME,
    DELETED_SENDER_DISPLAY_NAME,
    DEFAULT_AVATAR_PATH,
    DELETED_AVATAR_PATH,
)


class MessageStore:
    def __init__(self):
        self._messages: Dict[str, List[MessageRead]] = {}
        self._message_id = 0
        self._lock = threading.Lock()

    def generate_id(self) -> int:
        with self._lock:
            self._message_id += 1
            return self._message_id

    def add_message(
        self,
        message: MessageCreate,
        character_name: str,
        sender_username: Optional[str] = None,
        avatar_url: Optional[str] = None,
        ooc_as_user: bool = False,
    ) -> MessageRead:
        with self._lock:
            self._message_id += 1
            msg = MessageRead(
                id=self._message_id,
                text=message.text,
                character_name=character_name,
                sender_username=sender_username,
                avatar_url=avatar_url,
                location_id=message.location_id,
                is_ooc=message.is_ooc,
                ooc_as_user=ooc_as_user,
                created_at=datetime.now(UTC),
            )
            if message.location_id not in self._messages:
                self._messages[message.location_id] = []
            self._messages[message.location_id].append(msg)
            return msg

    def get_messages(self, location_id: str, limit: int = 100) -> List[MessageRead]:
        messages = self._messages.get(location_id, [])
        return messages[-limit:]

    def get_deleted_avatar(self) -> str:
        """Return path to deleted entity avatar."""
        return DELETED_AVATAR_PATH

    def get_deleted_display_name(
        self,
        entity_type: str = "sender",
        original_name: Optional[str] = None,
    ) -> str:
        """Return display name for deleted entity."""
        if entity_type == "user":
            return DELETED_USER_DISPLAY_NAME
        elif entity_type == "character":
            return DELETED_CHARACTER_DISPLAY_NAME
        else:
            if original_name:
                return f"{DELETED_SENDER_DISPLAY_NAME} ({original_name})"
            return DELETED_SENDER_DISPLAY_NAME


message_store = MessageStore()

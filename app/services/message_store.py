from datetime import datetime, UTC
from typing import Dict, List, Optional
from app.schemas.schemas import MessageCreate, MessageRead


class MessageStore:
    def __init__(self):
        self._messages: Dict[int, List[MessageRead]] = {}
        self._message_id = 0

    def generate_id(self) -> int:
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

    def get_messages(self, location_id: int, limit: int = 100) -> List[MessageRead]:
        messages = self._messages.get(location_id, [])
        return messages[-limit:]


message_store = MessageStore()

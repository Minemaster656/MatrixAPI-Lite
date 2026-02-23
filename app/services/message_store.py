from datetime import datetime, UTC
from typing import Dict, List
from app.schemas.schemas import MessageCreate, MessageRead


class MessageStore:
    def __init__(self):
        self._messages: Dict[int, List[MessageRead]] = {}
        self._message_id = 0

    def generate_id(self) -> int:
        self._message_id += 1
        return self._message_id

    def add_message(self, message: MessageCreate) -> MessageRead:
        self._message_id += 1
        msg = MessageRead(
            id=self._message_id,
            text=message.text,
            character_name=message.character_name,
            location_id=message.location_id,
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

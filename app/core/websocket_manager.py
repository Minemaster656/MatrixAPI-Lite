from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from app.core.config import CHARACTER_FADEOUT_MESSAGE_COUNT


@dataclass
class FadingCharacter:
    """
    Character that was switched away from, gradually fading from online list.

    WHY: Shows previous character presence for context during transition.
    HOW: Decrements message_count on each message, removed when reaches 0.
    """

    username: str
    character_name: str
    character_id: int
    avatar_url: Optional[str]
    messages_left: int = CHARACTER_FADEOUT_MESSAGE_COUNT


@dataclass
class ConnectionInfo:
    username: str
    character_name: Optional[str]
    character_id: Optional[int]
    avatar_url: Optional[str]
    location_id: Optional[int]
    is_ooc: bool = False
    ooc_username: Optional[str] = None
    fading_characters: List[FadingCharacter] = field(default_factory=list)


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[WebSocket, ConnectionInfo] = {}

    async def connect(
        self,
        websocket: WebSocket,
        username: str = "Anonymous",
        character_name: Optional[str] = None,
        character_id: Optional[int] = None,
        avatar_url: Optional[str] = None,
        location_id: Optional[int] = None,
    ):
        await websocket.accept()
        self.active_connections[websocket] = ConnectionInfo(
            username=username,
            character_name=character_name,
            character_id=character_id,
            avatar_url=avatar_url,
            location_id=location_id,
        )

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            del self.active_connections[websocket]

    def get_info(self, websocket: WebSocket) -> ConnectionInfo:
        return self.active_connections.get(
            websocket, ConnectionInfo("Anonymous", None, None, None, None)
        )

    def get_username(self, websocket: WebSocket) -> str:
        info = self.get_info(websocket)
        return info.character_name or info.username or "Anonymous"

    async def broadcast(self, message: str | dict, location_id: Optional[int] = None):
        for connection, info in self.active_connections.items():
            if location_id is None or info.location_id == location_id:
                if isinstance(message, dict):
                    import json

                    await connection.send_text(json.dumps(message))
                else:
                    await connection.send_text(message)

    async def send_personal(self, message: str | dict, websocket: WebSocket):
        if isinstance(message, dict):
            import json

            await websocket.send_text(json.dumps(message))
        else:
            await websocket.send_text(message)

    def find_connection_by_username(self, username: str) -> Optional[WebSocket]:
        for connection, info in self.active_connections.items():
            if info.username == username or info.character_name == username:
                return connection
        return None

    def set_location(self, websocket: WebSocket, location_id: int):
        if websocket in self.active_connections:
            self.active_connections[websocket].location_id = location_id

    def set_character(
        self,
        websocket: WebSocket,
        character_name: str,
        avatar_url: Optional[str] = None,
        character_id: Optional[int] = None,
    ):
        if websocket in self.active_connections:
            info = self.active_connections[websocket]
            if info.character_id and info.character_id != character_id:
                fading = FadingCharacter(
                    username=info.username,
                    character_name=info.character_name or "",
                    character_id=info.character_id,
                    avatar_url=info.avatar_url,
                )
                info.fading_characters.append(fading)
            info.character_name = character_name
            info.avatar_url = avatar_url
            info.character_id = character_id

    def set_username(self, websocket: WebSocket, username: str):
        if websocket in self.active_connections:
            self.active_connections[websocket].username = username

    def set_ooc(self, websocket: WebSocket, is_ooc: bool):
        if websocket in self.active_connections:
            self.active_connections[websocket].is_ooc = is_ooc

    def set_ooc_username(self, websocket: WebSocket, ooc_username: Optional[str]):
        if websocket in self.active_connections:
            self.active_connections[websocket].ooc_username = ooc_username

    def decrement_fading_messages(self, location_id: int):
        """
        Decrement message counter for all fading characters on location.

        WHY: Controls how long old characters remain visible in online list.
        HOW: Called on each message, removes characters when counter reaches 0.
        """
        for connection, info in self.active_connections.items():
            if info.location_id == location_id:
                info.fading_characters = [
                    FadingCharacter(
                        username=fc.username,
                        character_name=fc.character_name,
                        character_id=fc.character_id,
                        avatar_url=fc.avatar_url,
                        messages_left=fc.messages_left - 1,
                    )
                    for fc in info.fading_characters
                    if fc.messages_left > 1
                ]

    def get_users_on_location(self, location_id: int) -> list[dict]:
        users = []
        for connection, info in self.active_connections.items():
            if info.location_id == location_id:
                users.append(
                    {
                        "username": info.username,
                        "character_name": info.character_name,
                        "character_id": info.character_id,
                        "avatar_url": info.avatar_url,
                        "is_current": True,
                        "opacity": 1.0,
                    }
                )
                for fc in info.fading_characters:
                    opacity = fc.messages_left / CHARACTER_FADEOUT_MESSAGE_COUNT
                    users.append(
                        {
                            "username": fc.username,
                            "character_name": fc.character_name,
                            "character_id": fc.character_id,
                            "avatar_url": fc.avatar_url,
                            "is_current": False,
                            "opacity": opacity,
                        }
                    )
        return users


manager = ConnectionManager()

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum


class ConnectionState(Enum):
    PENDING = "pending"
    AUTHENTICATED = "authenticated"


@dataclass
class ConnectionInfo:
    username: str
    character_name: Optional[str]
    character_id: Optional[str]
    avatar_url: Optional[str]
    location_id: Optional[str]
    is_ooc: bool = False
    ooc_username: Optional[str] = None
    state: ConnectionState = ConnectionState.PENDING
    user_id: Optional[str] = None


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[WebSocket, ConnectionInfo] = {}

    async def connect(
        self,
        websocket: WebSocket,
        username: str = "Anonymous",
        character_name: Optional[str] = None,
        character_id: Optional[str] = None,
        avatar_url: Optional[str] = None,
        location_id: Optional[str] = None,
    ):
        await websocket.accept()
        self.active_connections[websocket] = ConnectionInfo(
            username=username,
            character_name=character_name,
            character_id=character_id,
            avatar_url=avatar_url,
            location_id=location_id,
            state=ConnectionState.PENDING,
        )

    def authenticate(
        self,
        websocket: WebSocket,
        user_id: str,
        username: str,
    ):
        if websocket in self.active_connections:
            info = self.active_connections[websocket]
            info.state = ConnectionState.AUTHENTICATED
            info.user_id = user_id
            info.username = username

    def is_authenticated(self, websocket: WebSocket) -> bool:
        info = self.get_info(websocket)
        return info.state == ConnectionState.AUTHENTICATED

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            del self.active_connections[websocket]

    def get_info(self, websocket: WebSocket) -> ConnectionInfo:
        return self.active_connections.get(
            websocket,
            ConnectionInfo(
                "Anonymous", None, None, None, None, state=ConnectionState.PENDING
            ),
        )

    def get_username(self, websocket: WebSocket) -> str:
        info = self.get_info(websocket)
        return info.character_name or info.username or "Anonymous"

    async def broadcast(self, message: str | dict, location_id: Optional[str] = None):
        for connection, info in self.active_connections.items():
            if info.state != ConnectionState.AUTHENTICATED:
                continue
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
            if info.state != ConnectionState.AUTHENTICATED:
                continue
            if info.username == username or info.character_name == username:
                return connection
        return None

    def set_location(self, websocket: WebSocket, location_id: str):
        if websocket in self.active_connections:
            self.active_connections[websocket].location_id = location_id

    def set_character(
        self,
        websocket: WebSocket,
        character_name: str,
        avatar_url: Optional[str] = None,
        character_id: Optional[str] = None,
    ):
        if websocket in self.active_connections:
            info = self.active_connections[websocket]
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

    def get_users_on_location(self, location_id: str) -> list[dict]:
        """
        Get all users on a location.

        WHY: Shows active characters grouped by user.
        HOW: Collects all connections on location, de-duplicates by character.
        """
        seen_characters: set = set()
        users = []

        for connection, info in self.active_connections.items():
            if info.state != ConnectionState.AUTHENTICATED:
                continue
            if info.location_id == location_id:
                key = (info.username, info.character_id)
                if key not in seen_characters:
                    seen_characters.add(key)
                    users.append(
                        {
                            "username": info.username,
                            "character_name": info.character_name,
                            "character_id": info.character_id,
                            "avatar_url": info.avatar_url,
                        }
                    )

        return users


manager = ConnectionManager()

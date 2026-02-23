from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class ConnectionInfo:
    username: str
    character_name: Optional[str]
    character_id: Optional[int]
    avatar_url: Optional[str]
    location_id: Optional[int]


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
            self.active_connections[websocket].character_name = character_name
            self.active_connections[websocket].avatar_url = avatar_url
            self.active_connections[websocket].character_id = character_id

    def set_username(self, websocket: WebSocket, username: str):
        if websocket in self.active_connections:
            self.active_connections[websocket].username = username

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
                    }
                )
        return users


manager = ConnectionManager()

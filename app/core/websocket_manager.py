from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Optional
from dataclasses import dataclass
from app.services.message_store import message_store
from app.schemas.schemas import MessageCreate


@dataclass
class ConnectionInfo:
    username: str
    character_name: Optional[str]
    location_id: Optional[int]


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[WebSocket, ConnectionInfo] = {}

    async def connect(
        self,
        websocket: WebSocket,
        username: str = "Anonymous",
        character_name: Optional[str] = None,
        location_id: Optional[int] = None,
    ):
        await websocket.accept()
        self.active_connections[websocket] = ConnectionInfo(
            username=username, character_name=character_name, location_id=location_id
        )

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            del self.active_connections[websocket]

    def get_info(self, websocket: WebSocket) -> ConnectionInfo:
        return self.active_connections.get(
            websocket, ConnectionInfo("Anonymous", None, None)
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

    async def send_personal(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    def set_location(self, websocket: WebSocket, location_id: int):
        if websocket in self.active_connections:
            self.active_connections[websocket].location_id = location_id

    def set_character(self, websocket: WebSocket, character_name: str):
        if websocket in self.active_connections:
            self.active_connections[websocket].character_name = character_name


manager = ConnectionManager()

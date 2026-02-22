from fastapi import APIRouter
from typing import List
from fastapi import WebSocket

router = APIRouter()


class ConnectionManager:
    """Manage WebSocket connections for a chat application."""

    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection and store it."""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a disconnected WebSocket from the list."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket) -> None:
        """Send a message to a single client."""
        await websocket.send_text(message)

    async def broadcast(self, message: str) -> None:
        """Send a message to all connected clients."""
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


@router.websocket("/ws/chat")
async def chat_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo the received message to all clients
            await manager.broadcast(data)
    except Exception:
        # Handle disconnects and any other errors gracefully
        pass
    finally:
        manager.disconnect(websocket)

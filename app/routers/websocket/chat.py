"""
WebSocket endpoint for real-time chat communication.

WHY: Enables real-time bidirectional communication for the chat system.
HOW: Uses FastAPI WebSocket with custom message protocol for:
     - Setting character identity
     - Joining/switching locations
     - Broadcasting messages to location participants
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlmodel import select, Session

from app.core.websocket_manager import manager
from app.core.db import engine
from app.models.models import Location
from app.services.message_store import message_store
from app.schemas.schemas import MessageCreate

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket) -> None:
    """
    Main WebSocket endpoint for chat functionality.

    WHY: Central real-time communication channel for all chat interactions.
    HOW: Maintains persistent connection and handles message routing:
         - 'message': Broadcasts text to current location
         - 'set_character': Associates websocket with character name
         - 'set_location': Joins location room and sends history

    Protocol messages:
        Client -> Server:
            {"type": "message", "text": "..."}
            {"type": "set_character", "character_name": "..."}
            {"type": "set_location", "location_id": int}

        Server -> Client:
            {"type": "message", "id": int, "text": "...", "character_name": "...", "created_at": "ISO"}
            {"type": "character_set", "character_name": "..."}
            {"type": "location_set", "location_id": int, "location_name": "...", "background_url": "...", "messages": [...]}
            {"type": "locations_list", "locations": [...]}
            {"type": "online_users", "users": [...]}
            {"type": "error", "message": "..."}

    Args:
        websocket: The WebSocket connection instance.

    Note:
        Connection is automatically cleaned up on disconnect,
        and other users are notified of the departure.
    """
    await manager.connect(websocket, username="Anonymous")
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "message":
                await _handle_message(websocket, data)
            elif msg_type == "set_character":
                await _handle_set_character(websocket, data)
            elif msg_type == "set_location":
                await _handle_set_location(websocket, data)

    except WebSocketDisconnect:
        await _handle_disconnect(websocket)


async def _handle_message(websocket: WebSocket, data: dict) -> None:
    """
    Handle incoming chat message.

    WHY: Routes messages to the correct location participants.
    HOW: Validates location is set, stores message, broadcasts to location.

    Args:
        websocket: The sender's WebSocket connection.
        data: Message data with 'text' field.
    """
    character_name = manager.get_username(websocket)
    location_id = manager.get_info(websocket).location_id

    if not location_id:
        await websocket.send_json({"type": "error", "message": "No location selected"})
        return

    text = data.get("text", "")
    if not text:
        return

    message = MessageCreate(
        text=text, character_name=character_name, location_id=location_id
    )
    msg = message_store.add_message(message)

    await manager.broadcast(
        {
            "type": "message",
            "id": msg.id,
            "text": msg.text,
            "character_name": msg.character_name,
            "created_at": msg.created_at.isoformat(),
        },
        location_id,
    )


async def _handle_set_character(websocket: WebSocket, data: dict) -> None:
    """
    Handle character identity setting.

    WHY: Associates the WebSocket connection with a character name.
    HOW: Updates connection metadata in the connection manager.

    Args:
        websocket: The WebSocket connection.
        data: Data with 'character_name' field.
    """
    character_name = data.get("character_name", "")
    manager.set_character(websocket, character_name)
    await websocket.send_json(
        {"type": "character_set", "character_name": character_name}
    )


async def _handle_set_location(websocket: WebSocket, data: dict) -> None:
    """
    Handle location join/switch.

    WHY: Manages user presence in location rooms and sends context.
    HOW: Updates room membership, sends history and online users.

    Args:
        websocket: The WebSocket connection.
        data: Data with 'location_id' field.
    """
    location_id = data.get("location_id")
    old_location_id = manager.get_info(websocket).location_id
    manager.set_location(websocket, location_id)
    messages = message_store.get_messages(location_id)

    with Session(engine) as session:
        location = session.get(Location, location_id)
        locations = session.exec(select(Location)).all()

    online_users = manager.get_users_on_location(location_id)

    await websocket.send_json(
        {
            "type": "location_set",
            "location_id": location_id,
            "location_name": location.name if location else "",
            "background_url": location.background_url if location else "",
            "messages": [
                {
                    "id": m.id,
                    "text": m.text,
                    "character_name": m.character_name,
                    "created_at": m.created_at.isoformat(),
                }
                for m in messages
            ],
        }
    )

    await websocket.send_json(
        {
            "type": "locations_list",
            "locations": [{"id": loc.id, "name": loc.name} for loc in locations],
        }
    )

    await websocket.send_json({"type": "online_users", "users": online_users})

    if old_location_id and old_location_id != location_id:
        await manager.broadcast(
            {
                "type": "online_users",
                "users": manager.get_users_on_location(old_location_id),
            },
            old_location_id,
        )

    await manager.broadcast(
        {
            "type": "online_users",
            "users": manager.get_users_on_location(location_id),
        },
        location_id,
    )


async def _handle_disconnect(websocket: WebSocket) -> None:
    """
    Handle WebSocket disconnection.

    WHY: Cleans up connection state and notifies other users.
    HOW: Removes from manager and broadcasts updated user list.

    Args:
        websocket: The disconnected WebSocket connection.
    """
    info = manager.get_info(websocket)
    location_id = info.location_id
    manager.disconnect(websocket)
    if location_id:
        await manager.broadcast(
            {
                "type": "online_users",
                "users": manager.get_users_on_location(location_id),
            },
            location_id,
        )

"""
WebSocket endpoint for real-time chat communication.

WHY: Enables real-time bidirectional communication for the chat system.
HOW: Uses FastAPI WebSocket with custom message protocol for:
     - Setting character identity
     - Joining/switching locations
     - Broadcasting messages to location participants
"""

from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlmodel import select, Session

from app.core.websocket_manager import manager
from app.core.db import engine
from app.models.models import Character, Location
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
            elif msg_type == "private_message":
                await _handle_private_message(websocket, data)
            elif msg_type == "set_character":
                await _handle_set_character(websocket, data)
            elif msg_type == "set_location":
                await _handle_set_location(websocket, data)
            elif msg_type == "set_ooc":
                await _handle_set_ooc(websocket, data)

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
    info = manager.get_info(websocket)
    is_ooc = info.is_ooc
    ooc_as_user = is_ooc and info.ooc_username is not None

    if is_ooc and info.ooc_username:
        character_name = info.ooc_username
        avatar_url = None
    else:
        character_name = info.character_name or info.username or "Anonymous"
        avatar_url = info.avatar_url

    sender_username = info.username
    location_id = info.location_id

    if not location_id:
        await websocket.send_json({"type": "error", "message": "No location selected"})
        return

    text = data.get("text", "")
    if not text:
        return

    message = MessageCreate(text=text, location_id=location_id, is_ooc=is_ooc)
    msg = message_store.add_message(
        message, character_name, sender_username, avatar_url, ooc_as_user
    )
    manager.decrement_fading_messages(location_id)

    await manager.broadcast(
        {
            "type": "message",
            "id": msg.id,
            "text": msg.text,
            "character_name": msg.character_name,
            "sender_username": msg.sender_username,
            "avatar_url": avatar_url,
            "is_ooc": msg.is_ooc,
            "ooc_as_user": msg.ooc_as_user,
            "created_at": msg.created_at.isoformat(),
        },
        location_id,
    )


async def _handle_private_message(websocket: WebSocket, data: dict) -> None:
    """
    Handle incoming private/direct message.

    WHY: Allows users to send private messages to each other.
    HOW: Finds target WebSocket by username, sends only to that user.

    Args:
        websocket: The sender's WebSocket connection.
        data: Message data with 'text' and 'target_username' fields.
    """
    info = manager.get_info(websocket)
    sender_name = info.character_name or info.username or "Anonymous"
    sender_avatar = info.avatar_url
    is_ooc = info.is_ooc
    target_username = data.get("target_username")
    text = data.get("text", "")

    if not target_username or not text:
        return

    target_websocket = manager.find_connection_by_username(target_username)
    if not target_websocket:
        await websocket.send_json(
            {"type": "error", "message": "User not found or offline"}
        )
        return

    message_payload = {
        "type": "private_message",
        "id": message_store.generate_id(),
        "text": text,
        "character_name": sender_name,
        "sender_username": info.username,
        "avatar_url": sender_avatar,
        "is_ooc": is_ooc,
        "created_at": datetime.now().isoformat(),
    }

    await manager.send_personal(message_payload, websocket)
    await manager.send_personal(message_payload, target_websocket)


async def _handle_set_character(websocket: WebSocket, data: dict) -> None:
    """
    Handle character identity setting.

    WHY: Associates the WebSocket connection with a character name.
    HOW: Updates connection metadata in the connection manager.
          Validates that character belongs to the authenticated user.

    Args:
        websocket: The WebSocket connection.
        data: Data with 'character_id', 'character_name', and optional 'token' fields.
    """
    character_id = data.get("character_id")
    character_name = data.get("character_name", "")
    username = data.get("username", "Anonymous")
    token = data.get("token")
    avatar_url = None
    user_id = None

    if token:
        from app.core.auth import decode_access_token

        payload = decode_access_token(token)
        if payload:
            sub = payload.get("sub")
            if sub is not None:
                user_id = int(sub)

    if character_id and user_id is not None:
        try:
            char_id_int = int(character_id)
        except (TypeError, ValueError):
            await websocket.send_json(
                {"type": "error", "message": "Invalid character_id"}
            )
            return
        with Session(engine) as session:
            character = session.get(Character, char_id_int)
            if character and character.owner_id == user_id:
                avatar_url = character.avatar_url
                character_name = character.name
            elif character:
                await websocket.send_json(
                    {"type": "error", "message": "Character does not belong to you"}
                )
                return

    manager.set_username(websocket, username)
    manager.set_character(websocket, character_name, avatar_url, character_id)

    info = manager.get_info(websocket)
    if info.location_id:
        await manager.broadcast(
            {
                "type": "online_users",
                "users": manager.get_users_on_location(info.location_id),
            },
            info.location_id,
        )

    await websocket.send_json(
        {
            "type": "character_set",
            "character_name": character_name,
            "character_id": character_id,
            "avatar_url": avatar_url,
        }
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
    if location_id is None:
        await websocket.send_json(
            {"type": "error", "message": "location_id is required"}
        )
        return

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
                    "sender_username": m.sender_username,
                    "avatar_url": m.avatar_url,
                    "is_ooc": m.is_ooc,
                    "ooc_as_user": m.ooc_as_user,
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


async def _handle_set_ooc(websocket: WebSocket, data: dict) -> None:
    """
    Handle OOC mode toggle.

    WHY: Allows users to switch between character and user identity.
    HOW: Updates is_ooc flag in connection info.
         If as_user is True, messages will be sent as the user (username).
         If as_user is False, messages will be sent as character but with [OOC] tag.

    Args:
        websocket: The WebSocket connection.
        data: Data with 'is_ooc' boolean field and optional 'as_user' boolean.
    """
    is_ooc = data.get("is_ooc", False)
    as_user = data.get("as_user", False)
    info = manager.get_info(websocket)
    if as_user:
        manager.set_ooc_username(websocket, info.username)
    else:
        manager.set_ooc_username(websocket, None)
    manager.set_ooc(websocket, is_ooc)
    await websocket.send_json({"type": "ooc_set", "is_ooc": is_ooc, "as_user": as_user})


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

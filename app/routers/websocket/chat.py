"""
WebSocket endpoint for real-time chat communication.

WHY: Enables real-time bidirectional communication for the chat system.
HOW: Uses FastAPI WebSocket with custom message protocol for:
     - Authentication via token (required before any other messages)
     - Setting character identity
     - Joining/switching locations
     - Broadcasting messages to location participants
"""

import html
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlmodel import select, Session

from app.core.websocket_manager import manager, ConnectionState
from app.core.db import engine
from app.core.auth import decode_access_token
from app.models.models import Character, Location
from app.services.message_store import message_store
from app.schemas.schemas import MessageCreate

router = APIRouter(tags=["websocket"])


def sanitize_text(text: str) -> str:
    """Sanitize text to prevent XSS."""
    return html.escape(text.strip())


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket) -> None:
    """
    Main WebSocket endpoint for chat functionality.

    Protocol:
        1. Client connects (PENDING state)
        2. Client MUST send auth message first:
           {"type": "auth", "token": "valid_jwt_token"}
        3. Server responds with auth_result:
           {"type": "auth_result", "success": true/false, "user_id": "...", "username": "..."}
        4. Only after successful auth, client can send other messages

    Message types after authentication:
        - message: Broadcast text to current location
        - private_message: Send to specific user
        - set_character: Set character identity
        - set_location: Join location room
        - set_ooc: Toggle OOC mode
    """
    await manager.connect(websocket, username="Anonymous")
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "auth":
                await _handle_auth(websocket, data)
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            else:
                if not manager.is_authenticated(websocket):
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": "Authentication required. Send auth message first.",
                        }
                    )
                    continue

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


async def _handle_auth(websocket: WebSocket, data: dict) -> None:
    """Handle authentication message."""
    token = data.get("token")
    if not token:
        await websocket.send_json(
            {"type": "auth_result", "success": False, "message": "Token is required"}
        )
        return

    payload = decode_access_token(token)
    if not payload:
        await websocket.send_json(
            {
                "type": "auth_result",
                "success": False,
                "message": "Invalid or expired token",
            }
        )
        return

    user_id = payload.get("sub")
    if not user_id:
        await websocket.send_json(
            {
                "type": "auth_result",
                "success": False,
                "message": "Invalid token payload",
            }
        )
        return

    from app.models.models import User

    with Session(engine) as session:
        user = session.get(User, user_id)
        if not user or not user.is_active or user.id is None:
            await websocket.send_json(
                {
                    "type": "auth_result",
                    "success": False,
                    "message": "User not found or inactive",
                }
            )
            return

        manager.authenticate(websocket, user_id=user.id, username=user.username)

    await websocket.send_json(
        {
            "type": "auth_result",
            "success": True,
            "user_id": user_id,
            "username": user.username,
        }
    )


async def _handle_message(websocket: WebSocket, data: dict) -> None:
    """Handle incoming chat message."""
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

    text = sanitize_text(text)

    message = MessageCreate(text=text, location_id=location_id, is_ooc=is_ooc)
    msg = message_store.add_message(
        message, character_name, sender_username, avatar_url, ooc_as_user
    )

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
    """Handle incoming private/direct message."""
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

    text = sanitize_text(text)

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
    """Handle character identity setting."""
    character_id = data.get("character_id")
    character_name = data.get("character_name", "")
    username = data.get("username", "Anonymous")
    token = data.get("token")
    avatar_url = None
    user_id = None

    info = manager.get_info(websocket)
    user_id = info.user_id

    if character_id and user_id is not None:
        with Session(engine) as session:
            character = session.get(Character, character_id)
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
    """Handle location join/switch."""
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
    """Handle OOC mode toggle."""
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
    """Handle WebSocket disconnection."""
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

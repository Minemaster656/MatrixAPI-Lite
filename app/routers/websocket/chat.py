from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlmodel import select, Session
from app.core.websocket_manager import manager
from app.core.db import engine
from app.models.models import Location
from app.services.message_store import message_store
from app.schemas.schemas import MessageCreate

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await manager.connect(websocket, username="Anonymous")
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "message":
                character_name = manager.get_username(websocket)
                location_id = manager.get_info(websocket).location_id

                if not location_id:
                    await websocket.send_json(
                        {"type": "error", "message": "No location selected"}
                    )
                    continue

                text = data.get("text", "")
                if not text:
                    continue

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

            elif msg_type == "set_character":
                character_name = data.get("character_name", "")
                manager.set_character(websocket, character_name)
                await websocket.send_json(
                    {"type": "character_set", "character_name": character_name}
                )

            elif msg_type == "set_location":
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
                        "locations": [
                            {"id": loc.id, "name": loc.name} for loc in locations
                        ],
                    }
                )

                await websocket.send_json(
                    {"type": "online_users", "users": online_users}
                )

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

    except WebSocketDisconnect:
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

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.websocket_manager import manager
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
                manager.set_location(websocket, location_id)
                messages = message_store.get_messages(location_id)
                await websocket.send_json(
                    {
                        "type": "location_set",
                        "location_id": location_id,
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

    except WebSocketDisconnect:
        manager.disconnect(websocket)

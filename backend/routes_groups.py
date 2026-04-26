import uuid
from datetime import datetime

from fastapi.responses import JSONResponse

from async_user_database import get_user_settings
from async_groups_database import (
    create_group,
    get_group,
    get_all_groups,
    join_group,
    get_group_messages,
    get_sync_payload,
)

from .app import app
from . import state
from .group_service import receive_message, receive_room


@app.get("/api/rooms")
async def api_rooms():
    rooms = await get_all_groups(include_not_joined=True)
    return JSONResponse(rooms)


@app.post("/api/rooms")
async def api_create_room(data: dict):
    name = data.get("name", "").strip()
    unique_name = data.get("unique_name", "").strip().lower()

    if not name:
        return {
            "ok": False,
            "error": "empty_name",
        }

    # Пароли пока отключены.
    room = await create_group(
        name=name,
        password="",
        created_by=state.NODE_ID,
        unique_name=unique_name,
    )

    # Локально группа сохранится как joined=True.
    # Для других peer group_service отправит public copy с joined=False.
    await receive_room(room, forward=True)

    return {
        "ok": True,
        "room": room,
    }


@app.post("/api/rooms/check")
async def api_check_room(data: dict):
    # Пароли пока отключены, оставляем endpoint для совместимости со старым фронтом.
    return {
        "ok": True,
    }


@app.post("/api/groups/join")
async def api_group_join(data: dict):
    room_id = data.get("room_id", "")

    if not room_id:
        return {
            "ok": False,
            "error": "empty_room_id",
        }

    group = await get_group(room_id)

    if not group:
        return {
            "ok": False,
            "error": "group_not_found",
        }

    if group.get("is_joined"):
        return {
            "ok": True,
            "room": group,
        }

    await join_group(room_id)

    return {
        "ok": True,
        "room": await get_group(room_id),
    }


@app.get("/api/messages")
async def api_messages(room_id: str = None):
    messages = await get_group_messages(room_id)
    return JSONResponse(messages)


@app.post("/api/send")
async def api_send(data: dict):
    config = await get_user_settings()

    username = data.get("username") or config.get("username") or "Аноним"
    text = data.get("message", "").strip()
    room_id = data.get("room_id") or "general"

    if not text:
        return {
            "ok": False,
            "error": "empty_message",
        }

    group = await get_group(room_id)

    if not group:
        return {
            "ok": False,
            "error": "group_not_found",
        }

    if not group.get("is_joined"):
        return {
            "ok": False,
            "error": "not_joined",
        }

    msg = {
        "message_id": str(uuid.uuid4()),
        "room_id": room_id,
        "sender_id": state.NODE_ID,
        "username": username,
        "message": text,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    saved = await receive_message(msg, forward=True)

    if not saved:
        return {
            "ok": False,
            "error": "message_not_saved",
        }

    return {
        "ok": True,
        "message": msg,
    }


@app.get("/messages")
async def p2p_messages():
    payload = await get_sync_payload()
    return JSONResponse(payload)
import uuid
from datetime import datetime

from fastapi.responses import JSONResponse

from user_database import get_user_settings
from groups_database import (
    create_group,
    get_group,
    get_all_groups,
    check_group_password,
    join_group,
    get_group_messages,
    get_sync_payload,
)

from .app import app
from . import state
from .group_service import receive_message, receive_room


@app.get("/api/rooms")
def api_rooms():
    return JSONResponse(get_all_groups(include_not_joined=True))


@app.post("/api/rooms")
def api_create_room(data: dict):
    name = data.get("name", "").strip()
    password = data.get("password", "")
    unique_name = data.get("unique_name", "").strip().lower()

    if not name:
        return {"ok": False, "error": "empty_name"}

    room = create_group(
        name=name,
        password=password,
        created_by=state.NODE_ID,
        unique_name=unique_name,
    )

    receive_room(room, forward=True)

    return {"ok": True, "room": room}


@app.post("/api/rooms/check")
def api_check_room(data: dict):
    room_id = data.get("room_id", "")
    password = data.get("password", "")

    return {"ok": check_group_password(room_id, password)}


@app.post("/api/groups/join")
def api_group_join(data: dict):
    room_id = data.get("room_id", "")
    password = data.get("password", "")
    creator_id = data.get("created_by", "")

    group = get_group(room_id)

    if not group:
        return {"ok": False, "error": "group_not_found"}

    if group.get("is_joined"):
        return {"ok": True, "room": group}

    if not group.get("has_password"):
        join_group(room_id)
        return {"ok": True, "room": get_group(room_id)}

    if not check_group_password(room_id, password):
        return {"ok": False, "error": "wrong_password"}

    join_group(room_id)
    return {"ok": True, "room": get_group(room_id)}


@app.get("/api/messages")
def api_messages(room_id: str = None):
    return JSONResponse(get_group_messages(room_id))


@app.post("/api/send")
def api_send(data: dict):
    config = get_user_settings()

    username = data.get("username") or config.get("username") or "Аноним"
    text = data.get("message", "").strip()
    room_id = data.get("room_id") or "general"

    if not text:
        return {"ok": False}

    group = get_group(room_id)

    if not group or not group.get("is_joined"):
        return {"ok": False, "error": "not_joined"}

    msg = {
        "message_id": str(uuid.uuid4()),
        "room_id": room_id,
        "sender_id": state.NODE_ID,
        "username": username,
        "message": text,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    receive_message(msg, forward=True)

    return {"ok": True, "message": msg}


@app.get("/messages")
def p2p_messages():
    return JSONResponse(get_sync_payload())
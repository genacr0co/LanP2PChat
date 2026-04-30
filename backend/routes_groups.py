import uuid
from datetime import datetime

from fastapi.responses import JSONResponse

from user_db.profile import get_user_settings

from groups_db.groups import (
    create_group,
    get_group,
    get_all_groups,
    join_group,
    leave_group,
    delete_group,
    rename_group,
)

from groups_db.messages import (
    delete_group_message,
    get_group_messages,
    get_group_messages_page,
)

from groups_db.sync import get_sync_payload


from .app import app
from . import state
from .group_service import (
    receive_message,
    receive_room,
    receive_group_message_delete,
)


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

    room = await create_group(
        name=name,
        password="",
        created_by=state.NODE_ID,
        unique_name=unique_name,
    )

    await receive_room(room, forward=True)

    return {
        "ok": True,
        "room": room,
    }


@app.post("/api/rooms/check")
async def api_check_room(data: dict):
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

    joined = await join_group(room_id)

    if not joined:
        return {
            "ok": False,
            "error": "join_failed",
        }

    return {
        "ok": True,
        "room": await get_group(room_id),
    }


@app.post("/api/groups/leave")
async def api_group_leave(data: dict):
    room_id = data.get("room_id", "")

    if not room_id:
        return {
            "ok": False,
            "error": "empty_room_id",
        }

    result = await leave_group(room_id)

    if not result.get("ok"):
        return result

    return result


@app.post("/api/groups/delete")
async def api_group_delete(data: dict):
    room_id = data.get("room_id", "")

    if not room_id:
        return {
            "ok": False,
            "error": "empty_room_id",
        }

    result = await delete_group(
        room_id=room_id,
        deleted_by=state.NODE_ID,
    )

    if not result.get("ok"):
        return result

    deleted_room = result.get("room")

    if deleted_room:
        await receive_room(deleted_room, forward=True)

    return result


@app.post("/api/groups/rename")
async def api_group_rename(data: dict):
    room_id = data.get("room_id", "")
    name = data.get("name", "").strip()

    if not room_id:
        return {
            "ok": False,
            "error": "empty_room_id",
        }

    if not name:
        return {
            "ok": False,
            "error": "empty_name",
        }

    result = await rename_group(
        room_id=room_id,
        new_name=name,
        updated_by=state.NODE_ID,
    )

    if not result.get("ok"):
        return result

    renamed_room = result.get("room")

    if renamed_room:
        await receive_room(renamed_room, forward=True)

    return result


@app.get("/api/messages")
async def api_messages(
    room_id: str = None,
    page: int = 0,
    limit: int = 40,
    before_created_at: str = None,
    before_message_id: str = None,
):
    if page:
        payload = await get_group_messages_page(
            room_id=room_id,
            limit=limit,
            before_created_at=before_created_at,
            before_message_id=before_message_id,
        )

        return JSONResponse(payload)

    messages = await get_group_messages(room_id)
    return JSONResponse(messages)


@app.post("/api/messages/delete")
async def api_group_message_delete(data: dict):
    message_id = data.get("message_id", "")
    room_id = data.get("room_id", "")

    if not message_id:
        return {
            "ok": False,
            "error": "empty_message_id",
        }

    if not room_id:
        return {
            "ok": False,
            "error": "empty_room_id",
        }

    result = await delete_group_message(
        message_id=message_id,
        room_id=room_id,
        deleted_by=state.NODE_ID,
    )

    if not result.get("ok"):
        return result

    deleted_message = result.get("message")

    if deleted_message:
        await receive_group_message_delete(deleted_message, forward=True)

    return result


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
        "is_deleted": False,
        "deleted_at": "",
        "deleted_by": "",
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
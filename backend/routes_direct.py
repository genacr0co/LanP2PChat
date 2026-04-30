import uuid
from datetime import datetime

from fastapi.responses import JSONResponse

from user_db.profile import get_user_settings

from direct_db.chats import (
    make_direct_chat_id,
    get_direct_chats,
    delete_direct_chat,
)

from direct_db.messages import (
    get_direct_messages,
    get_direct_messages_page,
    delete_direct_message,
)

from .app import app
from . import state
from .direct_service import (
    receive_direct_chat,
    receive_direct_message,
    receive_direct_message_delete,
    receive_direct_chat_delete,
)
from .p2p.api import send_packet_to_peer_async


@app.get("/api/direct/chats")
async def api_direct_chats():
    chats = await get_direct_chats()
    return JSONResponse(chats)


@app.post("/api/direct/start")
async def api_direct_start(data: dict):
    target_node_id = data.get("target_node_id", "")
    target_username = data.get("target_username", "Пользователь")

    if not target_node_id or target_node_id == state.NODE_ID:
        return {
            "ok": False,
            "error": "bad_target",
        }

    chat_id = make_direct_chat_id(state.NODE_ID, target_node_id)

    chat = {
        "chat_id": chat_id,
        "peer_id": target_node_id,
        "peer_name": target_username,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "is_deleted": False,
        "deleted_at": "",
        "deleted_by": "",
    }

    await receive_direct_chat(chat)

    return {
        "ok": True,
        "chat": chat,
    }


@app.get("/api/direct/messages")
async def api_direct_messages(
    chat_id: str,
    page: int = 0,
    limit: int = 40,
    before_created_at: str = None,
    before_message_id: str = None,
):
    if page:
        payload = await get_direct_messages_page(
            chat_id=chat_id,
            limit=limit,
            before_created_at=before_created_at,
            before_message_id=before_message_id,
        )

        return JSONResponse(payload)

    messages = await get_direct_messages(chat_id)
    return JSONResponse(messages)


@app.post("/api/direct/send")
async def api_direct_send(data: dict):
    config = await get_user_settings()

    target_node_id = data.get("target_node_id", "")
    target_username = data.get("target_username", "Пользователь")
    text = data.get("message", "").strip()

    if not target_node_id:
        return {
            "ok": False,
            "error": "bad_target",
        }

    if target_node_id == state.NODE_ID:
        return {
            "ok": False,
            "error": "self_message",
        }

    if not text:
        return {
            "ok": False,
            "error": "empty_message",
        }

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    chat_id = make_direct_chat_id(state.NODE_ID, target_node_id)

    my_chat = {
        "chat_id": chat_id,
        "peer_id": target_node_id,
        "peer_name": target_username,
        "created_at": now,
        "is_deleted": False,
        "deleted_at": "",
        "deleted_by": "",
    }

    peer_chat = {
        "chat_id": chat_id,
        "peer_id": state.NODE_ID,
        "peer_name": config.get("username", "Пользователь"),
        "created_at": now,
        "is_deleted": False,
        "deleted_at": "",
        "deleted_by": "",
    }

    msg = {
        "message_id": str(uuid.uuid4()),
        "chat_id": chat_id,
        "sender_id": state.NODE_ID,
        "username": config.get("username", "Аноним"),
        "message": text,
        "created_at": now,
        "is_deleted": False,
        "deleted_at": "",
        "deleted_by": "",
    }

    await receive_direct_chat(my_chat)
    await receive_direct_message(msg)

    sent = await send_packet_to_peer_async(target_node_id, {
        "type": "direct_message",
        "data": {
            "chat": peer_chat,
            "message": msg,
        },
    })

    return {
        "ok": True,
        "sent": sent,
        "chat": my_chat,
        "message": msg,
    }


@app.post("/api/direct/messages/delete")
async def api_direct_message_delete(data: dict):
    message_id = data.get("message_id", "")
    chat_id = data.get("chat_id", "")
    target_node_id = data.get("target_node_id", "")

    if not message_id:
        return {
            "ok": False,
            "error": "empty_message_id",
        }

    if not chat_id:
        return {
            "ok": False,
            "error": "empty_chat_id",
        }

    if not target_node_id:
        return {
            "ok": False,
            "error": "bad_target",
        }

    result = await delete_direct_message(
        message_id=message_id,
        chat_id=chat_id,
        deleted_by=state.NODE_ID,
    )

    if not result.get("ok"):
        return result

    deleted_message = result.get("message")

    if deleted_message:
        await receive_direct_message_delete(deleted_message)

        await send_packet_to_peer_async(target_node_id, {
            "type": "direct_message_deleted",
            "data": deleted_message,
        })

    return result


@app.post("/api/direct/chats/delete")
async def api_direct_chat_delete(data: dict):
    chat_id = data.get("chat_id", "")
    target_node_id = data.get("target_node_id", "")

    if not chat_id:
        return {
            "ok": False,
            "error": "empty_chat_id",
        }

    if not target_node_id:
        return {
            "ok": False,
            "error": "bad_target",
        }

    result = await delete_direct_chat(
        chat_id=chat_id,
        deleted_by=state.NODE_ID,
    )

    if not result.get("ok"):
        return result

    deleted_chat = result.get("chat")

    if deleted_chat:
        await receive_direct_chat_delete(deleted_chat)

        await send_packet_to_peer_async(target_node_id, {
            "type": "direct_chat_deleted",
            "data": deleted_chat,
        })

    return result


@app.get("/direct-sync")
async def p2p_direct_sync(peer_id: str):
    """
    P2P sync личных сообщений.

    peer_id — node_id того, кто запрашивает sync.
    Мы отдаём только direct-чат между текущим узлом и peer_id.
    """

    if not peer_id or peer_id == state.NODE_ID:
        return {
            "ok": False,
            "error": "bad_peer",
        }

    config = await get_user_settings()

    chat_id = make_direct_chat_id(state.NODE_ID, peer_id)
    messages = await get_direct_messages(chat_id)

    if not messages:
        return {
            "ok": True,
            "chat": None,
            "messages": [],
        }

    chat_for_peer = {
        "chat_id": chat_id,
        "peer_id": state.NODE_ID,
        "peer_name": config.get("username", "Пользователь"),
        "created_at": messages[0].get("created_at"),
        "is_deleted": False,
        "deleted_at": "",
        "deleted_by": "",
    }

    return {
        "ok": True,
        "chat": chat_for_peer,
        "messages": messages,
    }
import uuid
from datetime import datetime

from fastapi.responses import JSONResponse

from user_database import get_user_settings
from direct_database import (
    make_direct_chat_id,
    get_direct_chats,
    get_direct_messages,
)

from .app import app
from . import state
from .direct_service import receive_direct_chat, receive_direct_message
from .p2p_async import send_packet_to_peer


@app.get("/api/direct/chats")
def api_direct_chats():
    return JSONResponse(get_direct_chats())


@app.post("/api/direct/start")
def api_direct_start(data: dict):
    target_node_id = data.get("target_node_id", "")
    target_username = data.get("target_username", "Пользователь")

    if not target_node_id or target_node_id == state.NODE_ID:
        return {"ok": False}

    chat_id = make_direct_chat_id(state.NODE_ID, target_node_id)

    chat = {
        "chat_id": chat_id,
        "peer_id": target_node_id,
        "peer_name": target_username,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    receive_direct_chat(chat)

    return {
        "ok": True,
        "chat": chat,
    }


@app.get("/api/direct/messages")
def api_direct_messages(chat_id: str):
    return JSONResponse(get_direct_messages(chat_id))


@app.post("/api/direct/send")
def api_direct_send(data: dict):
    config = get_user_settings()

    target_node_id = data.get("target_node_id", "")
    target_username = data.get("target_username", "Пользователь")
    text = data.get("message", "").strip()

    if not target_node_id or not text:
        return {"ok": False}

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    chat_id = make_direct_chat_id(state.NODE_ID, target_node_id)

    my_chat = {
        "chat_id": chat_id,
        "peer_id": target_node_id,
        "peer_name": target_username,
        "created_at": now,
    }

    peer_chat = {
        "chat_id": chat_id,
        "peer_id": state.NODE_ID,
        "peer_name": config.get("username", "Пользователь"),
        "created_at": now,
    }

    msg = {
        "message_id": str(uuid.uuid4()),
        "chat_id": chat_id,
        "sender_id": state.NODE_ID,
        "username": config.get("username", "Аноним"),
        "message": text,
        "created_at": now,
    }

    receive_direct_chat(my_chat)
    receive_direct_message(msg)

    sent = send_packet_to_peer(target_node_id, {
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
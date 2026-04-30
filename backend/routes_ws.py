import json
import asyncio

from fastapi import WebSocket, WebSocketDisconnect

from settings import HTTP_PORT

from groups_db.groups import get_all_groups
from groups_db.messages import get_group_messages
from direct_db.chats import get_direct_chats

from .app import app
from . import state
from .services import handle_packet
from .p2p.peers import (
    add_or_update_peer as _add_or_update_peer,
    touch_peer as _touch_peer,
)


def _get_packet_data(packet):
    if not isinstance(packet, dict):
        return {}

    data = packet.get("data")

    if isinstance(data, dict):
        return data

    return {}


def _get_nested_message(packet):
    """
    Для direct_message пакет приходит примерно так:

    {
        "type": "direct_message",
        "data": {
            "chat": {...},
            "message": {
                "sender_id": "...",
                "username": "..."
            }
        }
    }

    Поэтому sender_id может быть не в data напрямую,
    а внутри data["message"].
    """
    data = _get_packet_data(packet)
    message = data.get("message")

    if isinstance(message, dict):
        return message

    return {}


def _extract_peer_node_id(packet):
    """
    Пытаемся достать node_id отправителя из разных форматов пакетов.

    Поддерживаем:
    - discovery-like packet
    - group_message
    - direct_message
    - group/room packet через created_by
    """
    if not isinstance(packet, dict):
        return None

    data = _get_packet_data(packet)
    nested_message = _get_nested_message(packet)

    return (
        packet.get("node_id")
        or packet.get("sender_id")
        or packet.get("from_node_id")
        or packet.get("created_by")
        or data.get("node_id")
        or data.get("sender_id")
        or data.get("from_node_id")
        or data.get("created_by")
        or nested_message.get("node_id")
        or nested_message.get("sender_id")
        or nested_message.get("from_node_id")
    )


def _extract_peer_username(packet):
    if not isinstance(packet, dict):
        return "Аноним"

    data = _get_packet_data(packet)
    nested_message = _get_nested_message(packet)

    return (
        packet.get("username")
        or packet.get("sender_name")
        or data.get("username")
        or data.get("sender_name")
        or nested_message.get("username")
        or nested_message.get("sender_name")
        or "Аноним"
    )


def _learn_peer_from_websocket_packet(websocket, packet):
    """
    Passive discovery.

    Если устройство уже прислало нам пакет по WebSocket,
    значит оно реально существует в LAN.

    Это не заменяет multicast/broadcast discovery,
    но помогает в случаях, когда Android/роутер режет UDP discovery.
    """
    peer_node_id = _extract_peer_node_id(packet)

    if not peer_node_id or peer_node_id == state.NODE_ID:
        return False

    client = websocket.client

    if not client:
        return False

    peer_ip = client.host

    if not peer_ip or peer_ip.startswith("127."):
        return False

    peer_packet = {
        "node_id": peer_node_id,
        "username": _extract_peer_username(packet),
        "ip": peer_ip,
        "port": packet.get("port") or HTTP_PORT,
        "platform": packet.get("platform", "unknown"),
    }

    return _add_or_update_peer(
        peer_packet,
        peer_ip,
        source="websocket",
    )


@app.websocket("/ws")
async def p2p_ws(websocket: WebSocket):
    await websocket.accept()

    peer_node_id = None

    try:
        while True:
            text = await websocket.receive_text()

            try:
                packet = json.loads(text)

                learned = _learn_peer_from_websocket_packet(websocket, packet)

                extracted_node_id = _extract_peer_node_id(packet)
                if extracted_node_id:
                    peer_node_id = extracted_node_id

                if learned and peer_node_id:
                    _touch_peer(peer_node_id)

                await handle_packet(packet)

            except Exception as e:
                print("[P2P WS ERROR]", e)

    except WebSocketDisconnect:
        pass

    finally:
        if peer_node_id:
            _touch_peer(peer_node_id)


@app.websocket("/ui/ws")
async def ui_ws(websocket: WebSocket):
    state.ui_loop = asyncio.get_running_loop()

    await websocket.accept()

    with state.web_clients_lock:
        state.local_web_clients.add(websocket)

    try:
        rooms = await get_all_groups(include_not_joined=True)
        messages = await get_group_messages()
        direct_chats = await get_direct_chats()

        for room in rooms:
            await websocket.send_text(json.dumps({
                "type": "room",
                "data": room,
            }, ensure_ascii=False))

        for msg in messages:
            await websocket.send_text(json.dumps({
                "type": "message",
                "data": msg,
            }, ensure_ascii=False))

        for chat in direct_chats:
            await websocket.send_text(json.dumps({
                "type": "direct_chat",
                "data": chat,
            }, ensure_ascii=False))

        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        pass

    finally:
        with state.web_clients_lock:
            state.local_web_clients.discard(websocket)
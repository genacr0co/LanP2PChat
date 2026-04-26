import json
import asyncio

from fastapi import WebSocket, WebSocketDisconnect

from async_groups_database import get_all_groups, get_group_messages
from async_direct_database import get_direct_chats

from .app import app
from . import state
from .services import handle_packet


@app.websocket("/ws")
async def p2p_ws(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            text = await websocket.receive_text()

            try:
                packet = json.loads(text)
                await handle_packet(packet)
            except Exception as e:
                print("[P2P WS ERROR]", e)

    except WebSocketDisconnect:
        pass


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
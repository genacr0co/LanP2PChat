import json
import time
import asyncio
import websockets

from settings import PEER_TIMEOUT

from .. import state

from .peers import (
    build_peer_hello_packet,
    touch_peer,
)


# =========================
# PEER HELLO
# =========================

async def send_peer_hello(websocket):
    """
    Отправляет identity-handshake сразу после открытия WebSocket.

    Это не чат-сообщение.
    Это служебный пакет, который помогает второй стороне узнать,
    кто к ней подключился.
    """
    try:
        packet = await build_peer_hello_packet()
        text = json.dumps(packet, ensure_ascii=False)
        await websocket.send(text)
        return True
    except Exception as e:
        print("[PEER HELLO SEND ERROR]", e)
        return False


# =========================
# PEER CONNECTION MANAGER
# =========================

async def peer_manager_loop():
    while True:
        now = time.time()

        with state.peer_lock:
            dead_peers = [
                node_id
                for node_id, peer in state.peers.items()
                if now - peer.get("last_seen", 0) > PEER_TIMEOUT
            ]

            for node_id in dead_peers:
                state.peers.pop(node_id, None)

                task = state.peer_tasks.pop(node_id, None)
                if task:
                    task.cancel()

                state.peer_connections.pop(node_id, None)
                state.peer_queues.pop(node_id, None)

            peer_list = list(state.peers.values())

        for peer in peer_list:
            await ensure_peer_task(peer)

        await asyncio.sleep(1)


async def ensure_peer_task(peer):
    """
    ВАЖНО:
    Эта функция должна выполняться только внутри state.network_loop.
    Не вызывай её напрямую из FastAPI routes.
    """
    node_id = peer.get("node_id")

    if not node_id:
        return False

    with state.peer_lock:
        task = state.peer_tasks.get(node_id)

        if task and not task.done():
            return True

        queue = state.peer_queues.get(node_id)

        if not queue:
            queue = asyncio.Queue()
            state.peer_queues[node_id] = queue

        task = asyncio.create_task(peer_connection_task(peer, queue))
        state.peer_tasks[node_id] = task

    return True


async def peer_connection_task(peer, queue):
    node_id = peer["node_id"]
    url = f"ws://{peer['ip']}:{peer['port']}/ws"

    while True:
        try:
            async with websockets.connect(
                url,
                ping_interval=10,
                ping_timeout=5,
                close_timeout=2,
                max_queue=64,
            ) as websocket:

                with state.peer_lock:
                    state.peer_connections[node_id] = websocket

                touch_peer(node_id)

                # ВАЖНО:
                # Сразу представляемся второй стороне.
                # Это помогает Android увидеть ПК даже если Android не принимает
                # входящие UDP discovery-пакеты.
                await send_peer_hello(websocket)

                sender = asyncio.create_task(peer_sender_loop(websocket, queue))
                receiver = asyncio.create_task(
                    peer_receiver_loop(websocket, node_id)
                )

                done, pending = await asyncio.wait(
                    [sender, receiver],
                    return_when=asyncio.FIRST_EXCEPTION,
                )

                for task in pending:
                    task.cancel()

        except asyncio.CancelledError:
            break

        except Exception:
            pass

        finally:
            with state.peer_lock:
                state.peer_connections.pop(node_id, None)

        await asyncio.sleep(1)


async def peer_sender_loop(websocket, queue):
    while True:
        packet = await queue.get()

        try:
            text = json.dumps(packet, ensure_ascii=False)
            await websocket.send(text)

        except Exception:
            # Если отправка упала, соединение пересоздаст peer_connection_task.
            pass

        finally:
            queue.task_done()


async def peer_receiver_loop(websocket, peer_node_id=None):
    # Импорт внутри функции, чтобы не ловить circular import:
    # p2p -> services -> group/direct/search -> p2p
    from ..services import handle_packet

    async for text in websocket:
        try:
            touch_peer(peer_node_id)

            packet = json.loads(text)
            await handle_packet(packet)

        except Exception as e:
            print("[PEER RECEIVE ERROR]", e)
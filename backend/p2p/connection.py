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
    """
    Heartbeat manager.

    Каждое устройство отправляет broadcast discovery-сигнал.
    Когда мы получаем сигнал от peer-а, add_or_update_peer()
    обновляет peer["last_seen"].

    Если от КОНКРЕТНОГО peer-а нет сигнала дольше PEER_TIMEOUT,
    удаляем только этого peer-а.

    Важно:
    - не очищаем весь список peer-ов;
    - не удаляем всех при ошибке одного;
    - каждый peer проверяется отдельно по своему last_seen.
    """
    while True:
        now = time.time()

        with state.peer_lock:
            peers_to_remove = []

            for node_id, peer in state.peers.items():
                last_seen = peer.get("last_seen", 0)
                silence_time = now - last_seen

                if silence_time > PEER_TIMEOUT:
                    peers_to_remove.append(node_id)

            for node_id in peers_to_remove:
                peer = state.peers.get(node_id)

                username = "unknown"
                ip = "unknown"

                if peer:
                    username = peer.get("username", "unknown")
                    ip = peer.get("ip", "unknown")

                print(
                    f"[PEER HEARTBEAT TIMEOUT] "
                    f"remove node_id={node_id} username={username} ip={ip}"
                )

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

    reconnect_delay = 1

    while True:
        try:
            async with websockets.connect(
                url,
                ping_interval=15,
                ping_timeout=15,
                close_timeout=5,
                max_queue=128,
            ) as websocket:

                reconnect_delay = 1

                with state.peer_lock:
                    state.peer_connections[node_id] = websocket

                    current_peer = state.peers.get(node_id)
                    if current_peer:
                        current_peer["online"] = True

                touch_peer(node_id)

                print(f"[PEER CONNECTED] node_id={node_id} url={url}")

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

                for task in done:
                    try:
                        task.result()
                    except asyncio.CancelledError:
                        pass
                    except Exception as e:
                        print(
                            f"[PEER TASK ERROR] "
                            f"node_id={node_id} url={url} error={e}"
                        )

        except asyncio.CancelledError:
            break

        except Exception as e:
            print(f"[PEER CONNECTION ERROR] node_id={node_id} url={url} error={e}")

        finally:
            with state.peer_lock:
                state.peer_connections.pop(node_id, None)

            print(f"[PEER DISCONNECTED] node_id={node_id} url={url}")

        await asyncio.sleep(reconnect_delay)
        reconnect_delay = min(reconnect_delay * 2, 10)


async def peer_sender_loop(websocket, queue):
    while True:
        packet = await queue.get()

        try:
            text = json.dumps(packet, ensure_ascii=False)
            await websocket.send(text)

        except Exception as e:
            print("[PEER SEND ERROR]", e)
            raise

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
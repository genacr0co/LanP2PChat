import json
import socket
import struct
import time
import asyncio
import websockets

from async_user_database import get_user_settings

from settings import (
    HTTP_PORT,
    DISCOVERY_PORT,
    DISCOVERY_INTERVAL,
    PEER_TIMEOUT,
)

from . import state
from .utils import get_local_ip, get_broadcast_addresses


# =========================
# DISCOVERY CONFIG
# =========================

DISCOVERY_PACKET_TYPE = "LAN_P2P_CHAT_NODE"

# Локальный administratively scoped multicast-адрес.
# Он не должен уходить в интернет, используется только внутри LAN.
MULTICAST_GROUP = "239.255.42.99"

# TTL = 1 означает "только текущая локальная сеть".
MULTICAST_TTL = 1


# =========================
# PEER HELPERS
# =========================

def _safe_int(value, default):
    try:
        return int(value)
    except Exception:
        return default


def _get_platform_name():
    try:
        import platform
        return platform.system().lower() or "unknown"
    except Exception:
        return "unknown"


def _build_discovery_packet(config):
    return {
        "type": DISCOVERY_PACKET_TYPE,
        "node_id": state.NODE_ID,
        "username": config.get("username", "Аноним"),
        "ip": get_local_ip(),
        "port": HTTP_PORT,
        "platform": _get_platform_name(),
        "timestamp": time.time(),
    }


def _add_or_update_peer(packet, addr_ip, source):
    """
    Единая точка обновления state.peers.

    source:
    - "broadcast"
    - "multicast"
    - "websocket"
    - "manual" в будущем
    """
    if not isinstance(packet, dict):
        return False

    peer_node_id = packet.get("node_id")

    if not peer_node_id or peer_node_id == state.NODE_ID:
        return False

    packet_ip = packet.get("ip")
    peer_ip = addr_ip or packet_ip

    if not peer_ip:
        return False

    peer_port = _safe_int(packet.get("port"), HTTP_PORT)

    username = packet.get("username", "Аноним")
    platform_name = packet.get("platform", "unknown")

    now = time.time()

    restart_task = False

    with state.peer_lock:
        old_peer = state.peers.get(peer_node_id)

        if old_peer:
            old_ip = old_peer.get("ip")
            old_port = _safe_int(old_peer.get("port"), HTTP_PORT)

            if old_ip != peer_ip or old_port != peer_port:
                restart_task = True

        state.peers[peer_node_id] = {
            "node_id": peer_node_id,
            "username": username,
            "ip": peer_ip,
            "port": peer_port,
            "platform": platform_name,
            "source": source,
            "online": True,
            "last_seen": now,
        }

        if restart_task:
            task = state.peer_tasks.pop(peer_node_id, None)
            if task:
                task.cancel()

            state.peer_connections.pop(peer_node_id, None)

    return True


def _touch_peer(peer_node_id):
    """
    Обновляет last_seen для peer-а, если он уже известен.
    Это полезно, когда discovery временно не работает,
    но WebSocket-соединение реально живое.
    """
    if not peer_node_id or peer_node_id == state.NODE_ID:
        return False

    with state.peer_lock:
        peer = state.peers.get(peer_node_id)

        if not peer:
            return False

        peer["last_seen"] = time.time()
        peer["online"] = True

    return True


# =========================
# DISCOVERY SOCKET HELPERS
# =========================

def _create_discovery_send_socket():
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    try:
        udp.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, MULTICAST_TTL)
    except Exception:
        pass

    try:
        udp.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
    except Exception:
        pass

    try:
        local_ip = get_local_ip()
        if local_ip and local_ip != "127.0.0.1":
            udp.setsockopt(
                socket.IPPROTO_IP,
                socket.IP_MULTICAST_IF,
                socket.inet_aton(local_ip),
            )
    except Exception:
        pass

    return udp


def _create_discovery_listen_socket():
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except Exception:
        pass

    try:
        udp.bind(("", DISCOVERY_PORT))
    except Exception as e:
        print("[DISCOVERY LISTEN BIND ERROR]", e)
        udp.close()
        return None

    # Подключаемся к multicast-группе.
    # Важно: на Android этого мало — ещё нужен MulticastLock на Java/Kotlin стороне.
    try:
        mreq = struct.pack(
            "4s4s",
            socket.inet_aton(MULTICAST_GROUP),
            socket.inet_aton("0.0.0.0"),
        )
        udp.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    except Exception as e:
        print("[DISCOVERY MULTICAST JOIN WARNING]", e)

    udp.setblocking(False)
    return udp


# =========================
# DISCOVERY
# =========================

async def discovery_announce_loop():
    """
    Отправляет discovery-пакеты двумя способами:

    1. UDP multicast — основной способ для нормального LAN discovery.
    2. UDP broadcast — fallback для сетей/роутеров, где multicast нестабилен.

    Android всё равно должен держать WifiManager.MulticastLock,
    иначе система может фильтровать multicast/broadcast пакеты.
    """
    udp = _create_discovery_send_socket()

    try:
        while True:
            try:
                config = await get_user_settings()
                packet = _build_discovery_packet(config)
                data = json.dumps(packet, ensure_ascii=False).encode("utf-8")

                # Multicast announcement
                try:
                    udp.sendto(data, (MULTICAST_GROUP, DISCOVERY_PORT))
                except Exception as e:
                    print("[DISCOVERY MULTICAST SEND WARNING]", e)

                # Broadcast fallback
                for broadcast_ip in get_broadcast_addresses():
                    try:
                        udp.sendto(data, (broadcast_ip, DISCOVERY_PORT))
                    except Exception:
                        pass

            except Exception as e:
                print("[DISCOVERY ANNOUNCE ERROR]", e)

            await asyncio.sleep(DISCOVERY_INTERVAL)

    finally:
        udp.close()


async def discovery_broadcast_loop():
    """
    Старое имя оставлено для совместимости.
    Теперь внутри это общий announce loop:
    multicast + broadcast fallback.
    """
    await discovery_announce_loop()


async def discovery_listen_loop():
    """
    Один listener принимает и multicast, и broadcast discovery-пакеты.
    """
    udp = _create_discovery_listen_socket()

    if not udp:
        return

    loop = asyncio.get_running_loop()

    try:
        while True:
            try:
                data, addr = await loop.sock_recvfrom(udp, 4096)

                try:
                    packet = json.loads(data.decode("utf-8"))
                except Exception:
                    continue

                if packet.get("type") != DISCOVERY_PACKET_TYPE:
                    continue

                # addr[0] надёжнее, чем packet["ip"],
                # потому что это реальный IP отправителя в LAN.
                source_ip = addr[0] if addr else None

                # Пока невозможно точно узнать, пришёл пакет через multicast или broadcast,
                # потому что один socket принимает оба типа.
                # Но для логики это не важно: peer найден.
                _add_or_update_peer(packet, source_ip, source="discovery")

            except asyncio.CancelledError:
                break

            except Exception as e:
                print("[DISCOVERY LISTEN ERROR]", e)
                await asyncio.sleep(0.1)

    finally:
        udp.close()


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

                _touch_peer(node_id)

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
    # p2p_async -> services -> group/direct/search -> p2p_async
    from .services import handle_packet

    async for text in websocket:
        try:
            _touch_peer(peer_node_id)

            packet = json.loads(text)
            await handle_packet(packet)

        except Exception as e:
            print("[PEER RECEIVE ERROR]", e)


# =========================
# INTERNAL NETWORK LOOP SENDERS
# =========================

async def _send_packet_to_peer_in_network_loop(target_node_id, packet):
    """
    Внутренняя отправка.
    Должна выполняться только внутри state.network_loop.
    """
    if not target_node_id:
        return False

    with state.peer_lock:
        peer = state.peers.get(target_node_id)

    if not peer:
        return False

    ok = await ensure_peer_task(peer)

    if not ok:
        return False

    with state.peer_lock:
        queue = state.peer_queues.get(target_node_id)

    if not queue:
        return False

    await queue.put(packet)
    return True


async def _broadcast_packet_in_network_loop(packet):
    """
    Внутренний broadcast.
    Должен выполняться только внутри state.network_loop.
    """
    with state.peer_lock:
        peer_ids = list(state.peers.keys())

    ok_count = 0

    for node_id in peer_ids:
        ok = await _send_packet_to_peer_in_network_loop(node_id, packet)
        if ok:
            ok_count += 1

    return ok_count > 0


# =========================
# PUBLIC ASYNC API
# =========================

async def send_packet_to_peer_async(target_node_id, packet):
    """
    Безопасная async-отправка.

    Можно вызывать из:
    - FastAPI routes loop
    - UI WebSocket loop
    - network_loop

    Если вызвана не из network_loop — перекинет корутину в network_loop.
    """
    if not state.network_loop:
        return False

    current_loop = asyncio.get_running_loop()

    if current_loop is state.network_loop:
        return await _send_packet_to_peer_in_network_loop(target_node_id, packet)

    future = asyncio.run_coroutine_threadsafe(
        _send_packet_to_peer_in_network_loop(target_node_id, packet),
        state.network_loop,
    )

    wrapped = asyncio.wrap_future(future)
    return await wrapped


async def broadcast_packet_async(packet):
    """
    Безопасный async-broadcast.
    """
    if not state.network_loop:
        return False

    current_loop = asyncio.get_running_loop()

    if current_loop is state.network_loop:
        return await _broadcast_packet_in_network_loop(packet)

    future = asyncio.run_coroutine_threadsafe(
        _broadcast_packet_in_network_loop(packet),
        state.network_loop,
    )

    wrapped = asyncio.wrap_future(future)
    return await wrapped


# =========================
# LEGACY SYNC WRAPPERS
# =========================

def send_packet_to_peer(target_node_id, packet):
    """
    Старый sync-wrapper.
    Оставляем временно для совместимости.
    Лучше постепенно убрать из нового async-кода.
    """
    if not state.network_loop:
        return False

    future = asyncio.run_coroutine_threadsafe(
        _send_packet_to_peer_in_network_loop(target_node_id, packet),
        state.network_loop,
    )

    try:
        return future.result(timeout=2)
    except Exception:
        return False


def broadcast_packet(packet):
    """
    Старый sync-wrapper.
    Оставляем временно для совместимости.
    """
    if not state.network_loop:
        return False

    future = asyncio.run_coroutine_threadsafe(
        _broadcast_packet_in_network_loop(packet),
        state.network_loop,
    )

    try:
        return future.result(timeout=2)
    except Exception:
        return False


def broadcast_ws_packet(packet):
    return broadcast_packet(packet)


# =========================
# START NETWORK
# =========================

async def start_network_layer():
    state.network_loop = asyncio.get_running_loop()

    await asyncio.gather(
        discovery_announce_loop(),
        discovery_listen_loop(),
        peer_manager_loop(),
    )
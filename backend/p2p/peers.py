import time

from user_db.profile import get_user_settings

from settings import HTTP_PORT
from .. import state
from ..utils import get_local_ip


# =========================
# DISCOVERY CONFIG
# =========================

DISCOVERY_PACKET_TYPE = "LAN_P2P_CHAT_NODE"
PEER_HELLO_PACKET_TYPE = "peer_hello"

# Локальный administratively scoped multicast-адрес.
# Он не должен уходить в интернет, используется только внутри LAN.
MULTICAST_GROUP = "239.255.42.99"

# TTL = 1 означает "только текущая локальная сеть".
MULTICAST_TTL = 1


# =========================
# HELPERS
# =========================

def safe_int(value, default):
    try:
        return int(value)
    except Exception:
        return default


def get_platform_name():
    try:
        import platform
        return platform.system().lower() or "unknown"
    except Exception:
        return "unknown"


def build_discovery_packet(config):
    return {
        "type": DISCOVERY_PACKET_TYPE,
        "node_id": state.NODE_ID,
        "username": config.get("username", "Аноним"),
        "ip": get_local_ip(),
        "port": HTTP_PORT,
        "platform": get_platform_name(),
        "timestamp": time.time(),
    }


async def build_peer_hello_packet():
    """
    Служебный hello-пакет для WebSocket handshake.

    Нужен для ситуации, когда один peer увидел другой через UDP discovery
    и подключился к нему по WebSocket, но второй peer сам UDP discovery
    не принял.

    Пример:
    - Android отправил UDP hello
    - ПК увидел Android
    - ПК подключился к Android по WebSocket
    - ПК сразу отправил peer_hello
    - Android добавил ПК в state.peers через routes_ws passive discovery
    """
    try:
        config = await get_user_settings()
    except Exception:
        config = {}

    return {
        "type": PEER_HELLO_PACKET_TYPE,
        "node_id": state.NODE_ID,
        "username": config.get("username", "Аноним"),
        "ip": get_local_ip(),
        "port": HTTP_PORT,
        "platform": get_platform_name(),
        "timestamp": time.time(),
    }


def add_or_update_peer(packet, addr_ip, source):
    """
    Единая точка обновления state.peers.

    source:
    - "broadcast"
    - "multicast"
    - "discovery"
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

    peer_port = safe_int(packet.get("port"), HTTP_PORT)

    username = packet.get("username", "Аноним")
    platform_name = packet.get("platform", "unknown")

    now = time.time()

    restart_task = False

    with state.peer_lock:
        old_peer = state.peers.get(peer_node_id)

        if old_peer:
            old_ip = old_peer.get("ip")
            old_port = safe_int(old_peer.get("port"), HTTP_PORT)

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


def touch_peer(peer_node_id):
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
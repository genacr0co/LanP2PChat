import asyncio
import json
import time

from settings import (
    HTTP_PORT,
    BOOTSTRAP_NODES,
    PEX_INTERVAL,
    PEX_MAX_PEERS,
    PEX_CONNECT_LIMIT,
)

from user_db.profile import get_user_settings

from .. import state
from ..utils import get_local_ip

from .peers import add_or_update_peer, get_platform_name, safe_int


PEX_REQUEST_TYPE = "pex_request"
PEX_RESPONSE_TYPE = "pex_response"


# =========================
# BOOTSTRAP HELPERS
# =========================

def normalize_node_address(value):
    """
    Поддерживает форматы:
    - "host:8765"
    - "http://host:8765"
    - "ws://host:8765/ws"
    - {"host": "host", "port": 8765}
    """
    host = None
    port = HTTP_PORT

    if isinstance(value, dict):
        host = value.get("host") or value.get("ip") or value.get("address")
        port = safe_int(value.get("port"), HTTP_PORT)

    elif isinstance(value, str):
        text = value.strip()

        if text.startswith("http://"):
            text = text[len("http://"):]
        elif text.startswith("https://"):
            text = text[len("https://"):]
        elif text.startswith("ws://"):
            text = text[len("ws://"):]
        elif text.startswith("wss://"):
            text = text[len("wss://"):]

        if "/" in text:
            text = text.split("/", 1)[0]

        if text.startswith("[") and "]" in text:
            # IPv6 сейчас не используем, но не падаем.
            host_part, _, rest = text[1:].partition("]")
            host = host_part
            if rest.startswith(":"):
                port = safe_int(rest[1:], HTTP_PORT)
        elif ":" in text:
            host_part, port_part = text.rsplit(":", 1)
            host = host_part.strip()
            port = safe_int(port_part.strip(), HTTP_PORT)
        else:
            host = text

    if not host:
        return None

    return {
        "host": str(host).strip(),
        "port": safe_int(port, HTTP_PORT),
    }


def get_bootstrap_nodes():
    nodes = []
    seen = set()

    for item in BOOTSTRAP_NODES:
        node = normalize_node_address(item)
        if not node:
            continue

        key = f"{node['host']}:{node['port']}"
        if key in seen:
            continue

        seen.add(key)
        nodes.append(node)

    return nodes


async def _http_get_json(host, port, path="/api/me", timeout=2.0):
    reader = None
    writer = None

    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout,
        )

        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            "User-Agent: LanP2PChat-Bootstrap\r\n"
            "Connection: close\r\n"
            "Accept: application/json\r\n"
            "\r\n"
        )

        writer.write(request.encode("utf-8"))
        await writer.drain()

        raw = await asyncio.wait_for(reader.read(65536), timeout=timeout)
        if not raw:
            return None

        text = raw.decode("utf-8", errors="ignore")
        if "\r\n\r\n" not in text:
            return None

        headers, body = text.split("\r\n\r\n", 1)
        status_line = headers.split("\r\n", 1)[0]

        if "200" not in status_line:
            return None

        return json.loads(body)

    except Exception:
        return None

    finally:
        if writer is not None:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass


# =========================
# PEER LIST BUILDING
# =========================

async def build_self_peer_info():
    try:
        config = await get_user_settings()
    except Exception:
        config = {}

    return {
        "node_id": state.NODE_ID,
        "username": config.get("username", "Аноним"),
        "ip": get_local_ip(),
        "port": HTTP_PORT,
        "platform": get_platform_name(),
        "source": "self",
        "online": True,
        "last_seen": time.time(),
    }


async def build_known_peers_payload(include_self=True, limit=None):
    if limit is None:
        limit = PEX_MAX_PEERS

    peers = []
    seen = set()

    if include_self:
        self_peer = await build_self_peer_info()
        if self_peer.get("node_id"):
            peers.append(self_peer)
            seen.add(self_peer["node_id"])

    with state.peer_lock:
        known = list(state.peers.values())

    # Сначала отдаём тех, кто недавно был онлайн.
    known.sort(key=lambda item: float(item.get("last_seen", 0) or 0), reverse=True)

    for peer in known:
        if not isinstance(peer, dict):
            continue

        node_id = peer.get("node_id")
        if not node_id or node_id == state.NODE_ID or node_id in seen:
            continue

        peers.append({
            "node_id": node_id,
            "username": peer.get("username", "Аноним"),
            "ip": peer.get("ip"),
            "port": safe_int(peer.get("port"), HTTP_PORT),
            "platform": peer.get("platform", "unknown"),
            "source": peer.get("source", "unknown"),
            "online": bool(peer.get("online", True)),
            "last_seen": peer.get("last_seen", 0),
        })
        seen.add(node_id)

        if len(peers) >= limit:
            break

    return peers


async def build_pex_request_packet():
    config = await get_user_settings()
    return {
        "type": PEX_REQUEST_TYPE,
        "node_id": state.NODE_ID,
        "username": config.get("username", "Аноним"),
        "ip": get_local_ip(),
        "port": HTTP_PORT,
        "platform": get_platform_name(),
        "timestamp": time.time(),
    }


async def build_pex_response_packet():
    return {
        "type": PEX_RESPONSE_TYPE,
        "node_id": state.NODE_ID,
        "peers": await build_known_peers_payload(include_self=True),
        "timestamp": time.time(),
    }


async def send_json_to_websocket(websocket, packet):
    text = json.dumps(packet, ensure_ascii=False)

    # FastAPI WebSocket. Важно проверять send_text раньше send(),
    # потому что у FastAPI .send() ждёт ASGI-dict, а не строку.
    send_text = getattr(websocket, "send_text", None)
    if callable(send_text):
        await send_text(text)
        return True

    # websockets lib.
    send = getattr(websocket, "send", None)
    if callable(send):
        await send(text)
        return True

    return False


async def send_pex_request(websocket):
    try:
        packet = await build_pex_request_packet()
        return await send_json_to_websocket(websocket, packet)
    except Exception as e:
        print("[PEX REQUEST SEND ERROR]", e)
        return False


async def send_pex_response(websocket):
    try:
        packet = await build_pex_response_packet()
        return await send_json_to_websocket(websocket, packet)
    except Exception as e:
        print("[PEX RESPONSE SEND ERROR]", e)
        return False


# =========================
# LEARNING PEERS
# =========================

def _looks_like_usable_peer(peer):
    if not isinstance(peer, dict):
        return False

    node_id = peer.get("node_id")
    ip = peer.get("ip")

    if not node_id or node_id == state.NODE_ID:
        return False

    if not ip:
        return False

    return True


def learn_peer(peer, source="pex", fallback_ip=None):
    if not _looks_like_usable_peer(peer):
        return False

    node_id = peer.get("node_id")
    ip = fallback_ip or peer.get("ip")
    port = safe_int(peer.get("port"), HTTP_PORT)

    packet = {
        "node_id": node_id,
        "username": peer.get("username", "Аноним"),
        "ip": ip,
        "port": port,
        "platform": peer.get("platform", "unknown"),
    }

    return add_or_update_peer(packet, ip, source=source)


def process_pex_response(packet, source="pex"):
    if not isinstance(packet, dict):
        return 0

    peers = packet.get("peers")
    if not isinstance(peers, list):
        return 0

    added = 0
    limit = max(1, int(PEX_CONNECT_LIMIT))

    for peer in peers[:limit]:
        if learn_peer(peer, source=source):
            added += 1

    if added:
        print(f"[PEX] learned peers={added} source={source}")

    return added


def process_api_me_payload(payload, source="bootstrap", fallback_ip=None):
    if not isinstance(payload, dict):
        return 0

    added = 0

    main_peer = {
        "node_id": payload.get("node_id"),
        "username": None,
        "ip": payload.get("ip") or fallback_ip,
        "port": payload.get("port") or HTTP_PORT,
        "platform": payload.get("platform", "unknown"),
    }

    users = payload.get("users")
    if isinstance(users, list):
        for user in users:
            if not isinstance(user, dict):
                continue
            if user.get("node_id") == payload.get("node_id"):
                main_peer["username"] = user.get("username")
                break

    if not main_peer.get("username"):
        main_peer["username"] = payload.get("username") or "Аноним"

    if learn_peer(main_peer, source=source, fallback_ip=fallback_ip):
        added += 1

    if isinstance(users, list):
        for user in users[:PEX_CONNECT_LIMIT]:
            if learn_peer(user, source="peer_gossip"):
                added += 1

    return added


# =========================
# LOOPS
# =========================

async def bootstrap_loop():
    """
    Bootstrap-ноды — это просто известные адреса входа в сеть.
    Они не являются обязательным центральным сервером: после получения peer-ов
    клиенты общаются напрямую и сами раздают PEX дальше.
    """
    await asyncio.sleep(2)

    nodes = get_bootstrap_nodes()

    if not nodes:
        print("[BOOTSTRAP] no bootstrap nodes configured")
        return

    print(f"[BOOTSTRAP] nodes={nodes}")

    while True:
        for node in nodes:
            host = node["host"]
            port = node["port"]

            # Не пытаемся ходить сами в себя по своему локальному IP.
            if host in ("127.0.0.1", "localhost", get_local_ip()) and port == HTTP_PORT:
                continue

            payload = await _http_get_json(host, port, "/api/me", timeout=2.0)
            if not payload:
                continue

            added = process_api_me_payload(
                payload,
                source="bootstrap",
                fallback_ip=host,
            )

            if added:
                print(f"[BOOTSTRAP] learned={added} from={host}:{port}")

        await asyncio.sleep(max(15, int(PEX_INTERVAL)))


async def pex_refresh_loop():
    """
    Периодически запрашивает у уже подключённых peer-ов их список peer-ов.
    """
    await asyncio.sleep(5)

    while True:
        try:
            with state.peer_lock:
                connections = list(state.peer_connections.items())

            for node_id, websocket in connections:
                try:
                    ok = await send_pex_request(websocket)
                    if ok:
                        print(f"[PEX] request -> {node_id}")
                except Exception as e:
                    print(f"[PEX REFRESH ERROR] node_id={node_id} error={e}")

        except Exception as e:
            print("[PEX REFRESH LOOP ERROR]", e)

        await asyncio.sleep(max(10, int(PEX_INTERVAL)))

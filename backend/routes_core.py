from fastapi.responses import FileResponse

from settings import STATIC_DIR, HTTP_PORT
from async_user_database import get_user_settings, save_user_settings

from .app import app
from . import state
from .utils import get_local_ip, get_broadcast_addresses


@app.get("/")
async def index():
    return FileResponse(f"{STATIC_DIR}/index.html")


def _build_peer_info(peer, connected=False):
    return {
        "node_id": peer.get("node_id"),
        "username": peer.get("username", "Аноним"),
        "ip": peer.get("ip"),
        "port": peer.get("port", HTTP_PORT),
        "platform": peer.get("platform", "unknown"),
        "source": peer.get("source", "unknown"),
        "online": peer.get("online", True),
        "connected": connected,
        "last_seen": peer.get("last_seen", 0),
    }


@app.get("/api/me")
async def api_me():
    online_users = []

    with state.peer_lock:
        peers_count = len(state.peers)
        sockets_count = len(state.peer_connections)

        for peer in state.peers.values():
            node_id = peer.get("node_id")
            connected = node_id in state.peer_connections

            online_users.append({
                "node_id": node_id,
                "username": peer.get("username", "Аноним"),
                "ip": peer.get("ip"),
                "port": peer.get("port", HTTP_PORT),
                "platform": peer.get("platform", "unknown"),
                "source": peer.get("source", "unknown"),
                "online": peer.get("online", True),
                "connected": connected,
                "last_seen": peer.get("last_seen", 0),
            })

    config = await get_user_settings()

    online_users.insert(0, {
        "node_id": state.NODE_ID,
        "username": config.get("username", "Вы"),
        "ip": get_local_ip(),
        "port": HTTP_PORT,
        "platform": "self",
        "source": "self",
        "online": True,
        "connected": True,
        "me": True,
    })

    return {
        "node_id": state.NODE_ID,
        "ip": get_local_ip(),
        "port": HTTP_PORT,
        "peers": peers_count,
        "sockets": sockets_count,
        "broadcasts": get_broadcast_addresses(),
        "users": online_users,
    }


@app.get("/api/peers")
async def api_peers():
    peers = []

    with state.peer_lock:
        for peer in state.peers.values():
            node_id = peer.get("node_id")
            connected = node_id in state.peer_connections
            peers.append(_build_peer_info(peer, connected=connected))

    return {
        "node_id": state.NODE_ID,
        "ip": get_local_ip(),
        "port": HTTP_PORT,
        "peers_count": len(peers),
        "peers": peers,
    }


@app.get("/api/config")
async def api_config():
    return await get_user_settings()


@app.post("/api/config")
async def api_save_config(data: dict):
    await save_user_settings(data)
    return {"ok": True}
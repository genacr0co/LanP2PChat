from fastapi.responses import FileResponse

from settings import STATIC_DIR, HTTP_PORT
from async_user_database import get_user_settings, save_user_settings

from .app import app
from . import state
from .utils import get_local_ip, get_broadcast_addresses


@app.get("/")
async def index():
    return FileResponse(f"{STATIC_DIR}/index.html")


@app.get("/api/me")
async def api_me():
    online_users = []

    with state.peer_lock:
        peers_count = len(state.peers)
        sockets_count = len(state.peer_connections)

        for peer in state.peers.values():
            online_users.append({
                "node_id": peer["node_id"],
                "username": peer.get("username", "Аноним"),
                "online": True,
            })

    config = await get_user_settings()

    online_users.insert(0, {
        "node_id": state.NODE_ID,
        "username": config.get("username", "Вы"),
        "online": True,
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


@app.get("/api/config")
async def api_config():
    return await get_user_settings()


@app.post("/api/config")
async def api_save_config(data: dict):
    await save_user_settings(data)
    return {"ok": True}
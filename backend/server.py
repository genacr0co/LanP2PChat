import asyncio
import threading
import uvicorn

from async_user_database import init_user_db, get_or_create_node_id
from async_groups_database import init_groups_db
from async_direct_database import init_direct_db

from settings import HTTP_PORT
from .app import app
from . import state
from . import routes  # важно: регистрирует все routes
from .p2p_async import start_network_layer

from .sync_service import (
    group_sync_loop,
    direct_sync_loop,
    pending_retry_loop,
)


def run_api_server():
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=HTTP_PORT,
        log_level="info",
        ws="websockets",
        loop="asyncio",
        access_log=True,
    )

    server = uvicorn.Server(config)
    server.run()


async def init_databases():
    await init_user_db()
    await init_groups_db()
    await init_direct_db()

    state.NODE_ID = await get_or_create_node_id()


async def run_background_async_tasks():
    await asyncio.gather(
        start_network_layer(),
        group_sync_loop(),
        direct_sync_loop(),
        pending_retry_loop(),
    )


def run_background_async_loop():
    asyncio.run(run_background_async_tasks())


def start_background_services():
    asyncio.run(init_databases())

    threading.Thread(target=run_api_server, daemon=True).start()
    threading.Thread(target=run_background_async_loop, daemon=True).start()
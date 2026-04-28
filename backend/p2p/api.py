import asyncio

from .. import state

from .discovery import (
    discovery_announce_loop,
    discovery_broadcast_loop,
    discovery_listen_loop,
)

from .connection import (
    peer_manager_loop,
    ensure_peer_task,
)


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
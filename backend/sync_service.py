import asyncio
import requests

from . import state
from .group_service import receive_group, receive_group_message


async def group_sync_from_peer(peer):
    """
    Backup-синхронизация групп.
    Личные сообщения здесь не трогаем.
    """

    url = f"http://{peer['ip']}:{peer['port']}/messages"

    try:
        response = await asyncio.to_thread(
            requests.get,
            url,
            timeout=2,
        )

        if response.status_code != 200:
            return False

        payload = response.json()

        for room in payload.get("rooms", []):
            receive_group(room, forward=False)

        for msg in payload.get("messages", []):
            receive_group_message(msg, forward=False)

        return True

    except Exception:
        return False


async def group_sync_loop():
    """
    Периодически подтягивает групповые сообщения у всех peer.
    Это backup, если WebSocket что-то пропустил.
    """

    while True:
        with state.peer_lock:
            peer_list = list(state.peers.values())

        for peer in peer_list:
            await group_sync_from_peer(peer)

        await asyncio.sleep(5)


async def direct_sync_loop():
    """
    Пока заглушка.
    Позже сюда добавим sync личных сообщений только между 2 peer.
    """

    while True:
        await asyncio.sleep(5)


async def pending_retry_loop():
    """
    Пока заглушка.
    Позже сюда добавим повторную отправку pending сообщений.
    """

    while True:
        await asyncio.sleep(5)
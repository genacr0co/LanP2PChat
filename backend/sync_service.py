import asyncio
import requests

from . import state
from .group_service import receive_group, receive_group_message


async def group_sync_from_peer(peer):
    """
    Backup-синхронизация групп.

    Забираем у peer-а только те группы/сообщения, которые он отдаёт через /messages.
    На нашей стороне receive_group_message() всё равно не сохранит сообщение,
    если мы не вступили в эту группу.
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
            await receive_group(room, forward=False)

        for msg in payload.get("messages", []):
            await receive_group_message(msg, forward=False)

        return True

    except Exception as e:
        print("[GROUP SYNC ERROR]", e)
        return False


async def group_sync_loop():
    """
    Периодически подтягивает групповые сообщения у всех online peer-ов.

    Это решает кейс:
    - ты был offline
    - в группе появились новые сообщения
    - ты вернулся online
    - если кто-то из участников группы online, ты подтянешь историю через /messages
    """

    while True:
        with state.peer_lock:
            peer_list = list(state.peers.values())

        for peer in peer_list:
            await group_sync_from_peer(peer)

        await asyncio.sleep(5)


async def direct_sync_from_peer(peer):
    """
    Backup-синхронизация личных сообщений между нами и конкретным peer.

    Мы спрашиваем у peer-а:
    "Есть ли у тебя сообщения direct-чата между мной и тобой?"

    Это решает кейс:
    - peer отправил нам сообщение, когда мы были offline
    - peer сохранил сообщение у себя
    - мы вернулись online
    - мы подтянули пропущенное сообщение у peer-а
    """

    if not state.NODE_ID:
        return False

    peer_node_id = peer.get("node_id")

    if not peer_node_id or peer_node_id == state.NODE_ID:
        return False

    url = f"http://{peer['ip']}:{peer['port']}/direct-sync"

    try:
        response = await asyncio.to_thread(
            requests.get,
            url,
            params={
                "peer_id": state.NODE_ID,
            },
            timeout=2,
        )

        if response.status_code != 200:
            return False

        payload = response.json()

        if not payload.get("ok"):
            return False

        chat = payload.get("chat")
        messages = payload.get("messages", [])

        from .direct_service import receive_direct_chat, receive_direct_message

        if chat:
            await receive_direct_chat(chat)

        for msg in messages:
            await receive_direct_message(msg)

        return True

    except Exception as e:
        print("[DIRECT SYNC ERROR]", e)
        return False


async def direct_sync_loop():
    """
    Периодически подтягивает личные сообщения у всех online peer-ов.
    """

    while True:
        with state.peer_lock:
            peer_list = list(state.peers.values())

        for peer in peer_list:
            await direct_sync_from_peer(peer)

        await asyncio.sleep(5)


async def pending_retry_loop():
    """
    Пока заглушка.

    Позже сюда можно добавить повторную отправку pending сообщений,
    если мы захотим явно хранить очередь недоставленных пакетов.
    Сейчас offline-доставка решается через pull-sync:
    - groups: /messages
    - direct: /direct-sync
    """

    while True:
        await asyncio.sleep(5)
from async_groups_database import save_group, save_group_message

from .utils import validate_message, validate_room
from .services import notify_ui
from .p2p_async import broadcast_packet_async


async def receive_group(data, forward=True):
    if not isinstance(data, dict):
        return False

    if not validate_room(data):
        return False

    room_id = data.get("room_id", "")

    # Личные комнаты сюда не пускаем
    if room_id.startswith("dm_") or room_id.startswith("direct_"):
        return False

    changed = await save_group(data)

    if not changed:
        return False

    packet = {
        "type": "group",
        "data": data,
    }

    await notify_ui(packet)

    if forward:
        await broadcast_packet_async(packet)

    return True


async def receive_room(data, forward=True):
    return await receive_group(data, forward)


async def receive_group_message(data, forward=True):
    if not isinstance(data, dict):
        return False

    if not data.get("room_id"):
        data["room_id"] = "general"

    room_id = data.get("room_id", "general")

    # Личные сообщения сюда не пускаем
    if room_id.startswith("dm_") or room_id.startswith("direct_"):
        return False

    if not validate_message(data):
        return False

    changed = await save_group_message(data)

    if not changed:
        return False

    await notify_ui({
        "type": "message",
        "data": data,
    })

    if forward:
        await broadcast_packet_async({
            "type": "group_message",
            "data": data,
        })

    return True


async def receive_message(data, forward=True):
    return await receive_group_message(data, forward)
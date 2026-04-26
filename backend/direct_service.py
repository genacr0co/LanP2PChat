from async_direct_database import save_direct_chat, save_direct_message
from .utils import validate_direct_chat, validate_direct_message
from .services import notify_ui


async def receive_direct_chat(data):
    if not validate_direct_chat(data):
        return False

    changed = await save_direct_chat(data)

    if changed:
        await notify_ui({
            "type": "direct_chat",
            "data": data,
        })

    return changed


async def receive_direct_message(data):
    if not validate_direct_message(data):
        return False

    changed = await save_direct_message(data)

    if changed:
        await notify_ui({
            "type": "direct_message",
            "data": data,
        })

    return changed


async def receive_direct_packet(data):
    if not isinstance(data, dict):
        return False

    chat = data.get("chat")
    message = data.get("message")

    if not chat or not message:
        return False

    await receive_direct_chat(chat)
    return await receive_direct_message(message)
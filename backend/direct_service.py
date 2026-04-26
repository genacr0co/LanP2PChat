from async_direct_database import save_direct_chat, save_direct_message

from .utils import validate_direct_chat, validate_direct_message
from .services import notify_ui


async def receive_direct_chat(data):
    if not isinstance(data, dict):
        return False

    if not validate_direct_chat(data):
        return False

    changed = await save_direct_chat(data)

    if not changed:
        return False

    await notify_ui({
        "type": "direct_chat",
        "data": data,
    })

    return True


async def receive_direct_message(data):
    if not isinstance(data, dict):
        return False

    if not validate_direct_message(data):
        return False

    changed = await save_direct_message(data)

    if not changed:
        return False

    await notify_ui({
        "type": "direct_message",
        "data": data,
    })

    return True


async def receive_direct_packet(data):
    if not isinstance(data, dict):
        return False

    chat = data.get("chat")
    message = data.get("message")

    if not isinstance(chat, dict) or not isinstance(message, dict):
        return False

    chat_changed = await receive_direct_chat(chat)
    message_changed = await receive_direct_message(message)

    return bool(chat_changed or message_changed)
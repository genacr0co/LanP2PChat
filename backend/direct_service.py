from async_direct_database import (
    save_direct_chat,
    save_direct_message,
    apply_direct_message_delete,
    apply_direct_chat_delete,
)

from .utils import validate_direct_chat, validate_direct_message
from .services import notify_ui


def normalize_direct_chat(data):
    normalized = dict(data)

    normalized["is_deleted"] = bool(normalized.get("is_deleted", False))
    normalized["deleted_at"] = normalized.get("deleted_at") or ""
    normalized["deleted_by"] = normalized.get("deleted_by") or ""

    return normalized


def normalize_direct_message(data):
    normalized = dict(data)

    normalized["is_deleted"] = bool(normalized.get("is_deleted", False))
    normalized["deleted_at"] = normalized.get("deleted_at") or ""
    normalized["deleted_by"] = normalized.get("deleted_by") or ""

    return normalized


async def receive_direct_chat(data):
    if not isinstance(data, dict):
        return False

    data = normalize_direct_chat(data)

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

    data = normalize_direct_message(data)

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


async def receive_direct_message_delete(data):
    """
    Принимает мягкое удаление личного сообщения.
    """

    if not isinstance(data, dict):
        return False

    result = await apply_direct_message_delete(data)

    if not result.get("ok"):
        return False

    deleted_message = result.get("message")

    if not deleted_message:
        return False

    await notify_ui({
        "type": "direct_message_deleted",
        "data": deleted_message,
    })

    return True


async def receive_direct_chat_delete(data):
    """
    Принимает мягкое удаление личного чата.
    """

    if not isinstance(data, dict):
        return False

    result = await apply_direct_chat_delete(data)

    if not result.get("ok"):
        return False

    deleted_chat = result.get("chat")

    if not deleted_chat:
        return False

    await notify_ui({
        "type": "direct_chat_deleted",
        "data": deleted_chat,
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
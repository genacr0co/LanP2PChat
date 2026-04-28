from groups_db.groups import save_group
from groups_db.messages import (
    save_group_message,
    apply_group_message_delete,
)

from . import state
from .utils import validate_message, validate_room
from .services import notify_ui
from .p2p.api import broadcast_packet_async


def make_public_group_copy(group):
    """
    Копия группы для других peer.

    Важно:
    - другой клиент НЕ должен автоматически становиться участником группы
    - другой клиент НЕ должен становиться creator
    - пароли пока полностью отключены
    - поля удаления обязательно сохраняем, чтобы P2P-удаление дошло до других
    """

    public_group = dict(group)

    public_group["is_creator"] = False
    public_group["is_joined"] = False
    public_group["has_password"] = False
    public_group["password_hash"] = ""

    public_group["is_deleted"] = bool(group.get("is_deleted"))
    public_group["deleted_at"] = group.get("deleted_at") or ""
    public_group["deleted_by"] = group.get("deleted_by") or ""

    return public_group


def normalize_received_group(group):
    """
    Если группа пришла от другого peer — не доверяем полям is_joined/is_creator.
    Иначе чужая группа может автоматически стать joined.

    Но полям удаления доверяем, потому что удаление должен получить каждый peer.
    """

    normalized = dict(group)

    created_by = normalized.get("created_by", "")

    if created_by != state.NODE_ID:
        normalized["is_creator"] = False
        normalized["is_joined"] = False
        normalized["has_password"] = False
        normalized["password_hash"] = ""

    normalized["is_deleted"] = bool(normalized.get("is_deleted"))
    normalized["deleted_at"] = normalized.get("deleted_at") or ""
    normalized["deleted_by"] = normalized.get("deleted_by") or ""

    return normalized


def normalize_group_message(data):
    normalized = dict(data)

    normalized["is_deleted"] = bool(normalized.get("is_deleted", False))
    normalized["deleted_at"] = normalized.get("deleted_at") or ""
    normalized["deleted_by"] = normalized.get("deleted_by") or ""

    return normalized


async def receive_group(data, forward=True):
    if not isinstance(data, dict):
        return False

    data = normalize_received_group(data)

    if not validate_room(data):
        return False

    room_id = data.get("room_id", "")

    if room_id.startswith("dm_") or room_id.startswith("direct_"):
        return False

    changed = await save_group(data)

    if not changed:
        return False

    await notify_ui({
        "type": "group",
        "data": data,
    })

    if forward:
        await broadcast_packet_async({
            "type": "group",
            "data": make_public_group_copy(data),
        })

    return True


async def receive_room(data, forward=True):
    return await receive_group(data, forward)


async def receive_group_message(data, forward=True):
    if not isinstance(data, dict):
        return False

    data = normalize_group_message(data)

    if not data.get("room_id"):
        data["room_id"] = "general"

    room_id = data.get("room_id", "general")

    if room_id.startswith("dm_") or room_id.startswith("direct_"):
        return False

    if not validate_message(data):
        return False

    # save_group_message сам проверяет is_joined/is_deleted.
    # Если пользователь не вступил в группу или группа удалена, сообщение не сохранится.
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


async def receive_group_message_delete(data, forward=True):
    """
    Принимает мягкое удаление группового сообщения.

    Работает и для локального API, и для P2P-пакета.
    """

    if not isinstance(data, dict):
        return False

    result = await apply_group_message_delete(data)

    if not result.get("ok"):
        return False

    deleted_message = result.get("message")

    if not deleted_message:
        return False

    await notify_ui({
        "type": "group_message_deleted",
        "data": deleted_message,
    })

    if forward:
        await broadcast_packet_async({
            "type": "group_message_deleted",
            "data": deleted_message,
        })

    return True


async def receive_message(data, forward=True):
    return await receive_group_message(data, forward)
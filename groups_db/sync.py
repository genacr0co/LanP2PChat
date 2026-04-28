from .groups import get_joined_groups
from .messages import get_group_messages


async def get_sync_payload():
    groups = await get_joined_groups()
    room_ids = {group["room_id"] for group in groups}

    all_messages = await get_group_messages()

    messages = [
        msg for msg in all_messages
        if msg.get("room_id") in room_ids
    ]

    return {
        "rooms": groups,
        "messages": messages,
    }
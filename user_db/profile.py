from .settings import get_setting, set_setting, get_or_create_node_id


async def get_user_settings():
    return {
        "username": await get_setting("username", ""),
        "node_id": await get_or_create_node_id(),
        "hide_deleted_messages": await get_setting("hide_deleted_messages", "false"),
    }


async def save_user_settings(data):
    if not isinstance(data, dict):
        return False

    if "username" in data:
        username = str(data.get("username") or "").strip()
        await set_setting("username", username)

    if "hide_deleted_messages" in data:
        value = data.get("hide_deleted_messages")
        enabled = value is True or str(value).lower() in ("1", "true", "yes", "on")
        await set_setting("hide_deleted_messages", "true" if enabled else "false")

    return True


async def get_username(default="Аноним"):
    username = await get_setting("username", "")
    return username or default
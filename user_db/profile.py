from .settings import get_setting, set_setting, get_or_create_node_id


async def get_user_settings():
    return {
        "username": await get_setting("username", ""),
        "node_id": await get_or_create_node_id(),
    }


async def save_user_settings(data):
    if not isinstance(data, dict):
        return False

    if "username" in data:
        username = str(data.get("username") or "").strip()
        await set_setting("username", username)

    return True


async def get_username(default="Аноним"):
    username = await get_setting("username", "")
    return username or default
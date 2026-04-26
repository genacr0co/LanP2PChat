import uuid
import aiosqlite

from settings import USER_DB_PATH


async def user_connect():
    return await aiosqlite.connect(USER_DB_PATH)


async def init_user_db():
    async with aiosqlite.connect(USER_DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS profile (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                node_id TEXT NOT NULL,
                username TEXT NOT NULL DEFAULT ''
            )
        """)

        node_id = await get_setting("node_id", "")
        username = await get_setting("username", "")

        if not node_id:
            node_id = str(uuid.uuid4())
            await set_setting("node_id", node_id)

        await db.execute("""
            INSERT OR IGNORE INTO profile (id, node_id, username)
            VALUES (1, ?, ?)
        """, (node_id, username))

        await db.commit()


async def get_setting(key, default=""):
    async with aiosqlite.connect(USER_DB_PATH) as db:
        cursor = await db.execute(
            "SELECT value FROM settings WHERE key = ?",
            (key,)
        )

        row = await cursor.fetchone()
        await cursor.close()

        return row[0] if row else default


async def set_setting(key, value):
    async with aiosqlite.connect(USER_DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO settings (key, value)
            VALUES (?, ?)
        """, (key, value))

        if key == "username":
            await db.execute("""
                UPDATE profile
                SET username = ?
                WHERE id = 1
            """, (value,))

        if key == "node_id":
            await db.execute("""
                UPDATE profile
                SET node_id = ?
                WHERE id = 1
            """, (value,))

        await db.commit()


async def get_or_create_node_id():
    node_id = await get_setting("node_id", "")

    if node_id:
        return node_id

    node_id = str(uuid.uuid4())
    await set_setting("node_id", node_id)
    return node_id


async def get_user_settings():
    return {
        "username": await get_setting("username", ""),
        "node_id": await get_or_create_node_id(),
    }


async def save_user_settings(data):
    if "username" in data:
        username = str(data.get("username") or "").strip()
        await set_setting("username", username)


async def get_username(default="Аноним"):
    username = await get_setting("username", "")
    return username or default
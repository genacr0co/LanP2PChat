import uuid

import aiosqlite

from settings import USER_DB_PATH


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

        cursor = await db.execute(
            "SELECT value FROM settings WHERE key = ?",
            ("node_id",),
        )
        row = await cursor.fetchone()
        await cursor.close()

        node_id = row[0] if row else ""

        if not node_id:
            node_id = str(uuid.uuid4())

            await db.execute("""
                INSERT OR REPLACE INTO settings (key, value)
                VALUES (?, ?)
            """, ("node_id", node_id))

        cursor = await db.execute(
            "SELECT value FROM settings WHERE key = ?",
            ("username",),
        )
        row = await cursor.fetchone()
        await cursor.close()

        username = row[0] if row else ""

        await db.execute("""
            INSERT INTO profile (id, node_id, username)
            VALUES (1, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                node_id = excluded.node_id,
                username = excluded.username
        """, (node_id, username))

        await db.commit()
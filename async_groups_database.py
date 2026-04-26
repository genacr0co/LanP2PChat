import uuid
import hashlib
from datetime import datetime

import aiosqlite

from settings import GROUPS_DB_PATH


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def hash_password(password):
    if not password:
        return ""

    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def group_row_to_dict(row, include_password_hash=True):
    data = {
        "room_id": row["room_id"],
        "name": row["name"],
        "unique_name": row["unique_name"],
        "created_by": row["created_by"],
        "created_at": row["created_at"],
        "is_creator": bool(row["is_creator"]),
        "is_joined": bool(row["is_joined"]),
        "has_password": bool(row["password_hash"]),
    }

    if include_password_hash:
        data["password_hash"] = row["password_hash"]

    return data


async def init_groups_db():
    async with aiosqlite.connect(GROUPS_DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                room_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                unique_name TEXT NOT NULL DEFAULT '',
                password_hash TEXT NOT NULL DEFAULT '',
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                is_creator INTEGER NOT NULL DEFAULT 0,
                is_joined INTEGER NOT NULL DEFAULT 0
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS group_messages (
                message_id TEXT PRIMARY KEY,
                room_id TEXT NOT NULL,
                sender_id TEXT NOT NULL,
                username TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_group_messages_room
            ON group_messages(room_id)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_group_messages_created_at
            ON group_messages(created_at)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_groups_unique_name
            ON groups(unique_name)
        """)

        await db.execute("""
            INSERT OR IGNORE INTO groups
            (room_id, name, unique_name, password_hash, created_by, created_at, is_creator, is_joined)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "general",
            "Общий чат",
            "general",
            "",
            "system",
            now_str(),
            1,
            1,
        ))

        await db.commit()


async def create_group(name, password, created_by, unique_name=""):
    room_id = str(uuid.uuid4())

    if not unique_name:
        unique_name = name.strip().lower()

    group = {
        "room_id": room_id,
        "name": name,
        "unique_name": unique_name,
        "password_hash": hash_password(password),
        "created_by": created_by,
        "created_at": now_str(),
        "is_creator": True,
        "is_joined": True,
        "has_password": bool(password),
    }

    await save_group(group)

    return group


async def save_group(group):
    room_id = group.get("room_id", "")

    if not room_id:
        return False

    if room_id.startswith("dm_") or room_id.startswith("direct_"):
        return False

    async with aiosqlite.connect(GROUPS_DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO groups
            (room_id, name, unique_name, password_hash, created_by, created_at, is_creator, is_joined)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(room_id) DO UPDATE SET
                name = excluded.name,
                unique_name = excluded.unique_name,
                password_hash = CASE
                    WHEN excluded.password_hash != '' THEN excluded.password_hash
                    ELSE groups.password_hash
                END,
                created_by = CASE
                    WHEN excluded.created_by != '' THEN excluded.created_by
                    ELSE groups.created_by
                END,
                created_at = CASE
                    WHEN excluded.created_at != '' THEN excluded.created_at
                    ELSE groups.created_at
                END,
                is_creator = CASE
                    WHEN groups.is_creator = 1 OR excluded.is_creator = 1 THEN 1
                    ELSE 0
                END,
                is_joined = CASE
                    WHEN groups.is_joined = 1 OR excluded.is_joined = 1 THEN 1
                    ELSE 0
                END
        """, (
            group["room_id"],
            group["name"],
            group.get("unique_name", ""),
            group.get("password_hash", ""),
            group.get("created_by", ""),
            group.get("created_at", now_str()),
            1 if group.get("is_creator") else 0,
            1 if group.get("is_joined") else 0,
        ))

        changed = cursor.rowcount > 0

        await cursor.close()
        await db.commit()

        return changed


async def save_discovered_group(group):
    if not isinstance(group, dict):
        return False

    room_id = group.get("room_id", "")

    if not room_id:
        return False

    if room_id.startswith("dm_") or room_id.startswith("direct_"):
        return False

    existing = await get_group(room_id)

    if existing:
        return False

    discovered = {
        "room_id": group["room_id"],
        "name": group["name"],
        "unique_name": group.get("unique_name", ""),
        "password_hash": group.get("password_hash", ""),
        "created_by": group.get("created_by", ""),
        "created_at": group.get("created_at") or now_str(),
        "is_creator": False,
        "is_joined": False,
    }

    return await save_group(discovered)


async def join_group(room_id):
    async with aiosqlite.connect(GROUPS_DB_PATH) as db:
        cursor = await db.execute("""
            UPDATE groups
            SET is_joined = 1
            WHERE room_id = ?
        """, (room_id,))

        changed = cursor.rowcount > 0

        await cursor.close()
        await db.commit()

        return changed


async def get_group(room_id):
    async with aiosqlite.connect(GROUPS_DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute("""
            SELECT room_id, name, unique_name, password_hash, created_by, created_at, is_creator, is_joined
            FROM groups
            WHERE room_id = ?
        """, (room_id,))

        row = await cursor.fetchone()
        await cursor.close()

        if not row:
            return None

        return group_row_to_dict(row)


async def get_all_groups(include_not_joined=True):
    async with aiosqlite.connect(GROUPS_DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        if include_not_joined:
            cursor = await db.execute("""
                SELECT room_id, name, unique_name, password_hash, created_by, created_at, is_creator, is_joined
                FROM groups
                ORDER BY created_at ASC
            """)
        else:
            cursor = await db.execute("""
                SELECT room_id, name, unique_name, password_hash, created_by, created_at, is_creator, is_joined
                FROM groups
                WHERE is_joined = 1
                ORDER BY created_at ASC
            """)

        rows = await cursor.fetchall()
        await cursor.close()

        return [group_row_to_dict(row) for row in rows]


async def get_joined_groups():
    return await get_all_groups(include_not_joined=False)


async def find_created_groups(query):
    q = (query or "").strip().lower()

    if not q:
        return []

    async with aiosqlite.connect(GROUPS_DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute("""
            SELECT room_id, name, unique_name, password_hash, created_by, created_at, is_creator, is_joined
            FROM groups
            WHERE is_creator = 1
              AND (
                  LOWER(name) LIKE ?
                  OR LOWER(unique_name) LIKE ?
              )
            ORDER BY created_at DESC
        """, (f"%{q}%", f"%{q}%"))

        rows = await cursor.fetchall()
        await cursor.close()

        return [
            {
                "room_id": row["room_id"],
                "name": row["name"],
                "unique_name": row["unique_name"],
                "created_by": row["created_by"],
                "created_at": row["created_at"],
                "has_password": bool(row["password_hash"]),
                # password_hash не отдаём в search response
            }
            for row in rows
        ]


async def check_group_password(room_id, password):
    group = await get_group(room_id)

    if not group:
        return False

    if not group["password_hash"]:
        return True

    return group["password_hash"] == hash_password(password)


async def save_group_message(data):
    room_id = data.get("room_id", "general")

    if room_id.startswith("dm_") or room_id.startswith("direct_"):
        return False

    group = await get_group(room_id)

    if not group or not group.get("is_joined"):
        return False

    async with aiosqlite.connect(GROUPS_DB_PATH) as db:
        cursor = await db.execute("""
            INSERT OR IGNORE INTO group_messages
            (message_id, room_id, sender_id, username, message, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data["message_id"],
            room_id,
            data["sender_id"],
            data["username"],
            data.get("message", ""),
            data["created_at"],
        ))

        changed = cursor.rowcount > 0

        await cursor.close()
        await db.commit()

        return changed


async def get_group_messages(room_id=None):
    if room_id:
        group = await get_group(room_id)

        if not group or not group.get("is_joined"):
            return []

    async with aiosqlite.connect(GROUPS_DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        if room_id:
            cursor = await db.execute("""
                SELECT message_id, room_id, sender_id, username, message, created_at
                FROM group_messages
                WHERE room_id = ?
                ORDER BY created_at ASC
            """, (room_id,))
        else:
            cursor = await db.execute("""
                SELECT message_id, room_id, sender_id, username, message, created_at
                FROM group_messages
                ORDER BY created_at ASC
            """)

        rows = await cursor.fetchall()
        await cursor.close()

        return [dict(row) for row in rows]


async def get_sync_payload():
    groups = await get_joined_groups()
    room_ids = {g["room_id"] for g in groups}

    messages = [
        m for m in await get_group_messages()
        if m.get("room_id") in room_ids
    ]

    return {
        "rooms": groups,
        "messages": messages,
    }
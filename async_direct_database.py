import uuid
from datetime import datetime

import aiosqlite

from settings import DIRECT_DB_PATH


DIRECT_MESSAGE_DELETE_MASK = "▒▒▒▒▒▒▒▒▒▒▒▒"


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


async def ensure_column(db, table_name, column_name, column_sql):
    cursor = await db.execute(f"PRAGMA table_info({table_name})")
    columns = await cursor.fetchall()
    await cursor.close()

    existing_columns = {col[1] for col in columns}

    if column_name not in existing_columns:
        await db.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}")


def direct_chat_row_to_dict(row):
    return {
        "chat_id": row["chat_id"],
        "peer_id": row["peer_id"],
        "peer_name": row["peer_name"],
        "created_at": row["created_at"],
        "is_deleted": bool(row["is_deleted"]),
        "deleted_at": row["deleted_at"] or "",
        "deleted_by": row["deleted_by"] or "",
    }


def direct_message_row_to_dict(row, mask_deleted=True):
    is_deleted = bool(row["is_deleted"])
    message = row["message"]

    if is_deleted and mask_deleted:
        message = DIRECT_MESSAGE_DELETE_MASK

    return {
        "message_id": row["message_id"],
        "chat_id": row["chat_id"],
        "sender_id": row["sender_id"],
        "username": row["username"],
        "message": message,
        "created_at": row["created_at"],
        "is_deleted": is_deleted,
        "deleted_at": row["deleted_at"] or "",
        "deleted_by": row["deleted_by"] or "",
    }


async def init_direct_db():
    async with aiosqlite.connect(DIRECT_DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS direct_chats (
                chat_id TEXT PRIMARY KEY,
                peer_id TEXT NOT NULL,
                peer_name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                is_deleted INTEGER NOT NULL DEFAULT 0,
                deleted_at TEXT NOT NULL DEFAULT '',
                deleted_by TEXT NOT NULL DEFAULT ''
            )
        """)

        await ensure_column(
            db,
            "direct_chats",
            "is_deleted",
            "is_deleted INTEGER NOT NULL DEFAULT 0",
        )

        await ensure_column(
            db,
            "direct_chats",
            "deleted_at",
            "deleted_at TEXT NOT NULL DEFAULT ''",
        )

        await ensure_column(
            db,
            "direct_chats",
            "deleted_by",
            "deleted_by TEXT NOT NULL DEFAULT ''",
        )

        await db.execute("""
            CREATE TABLE IF NOT EXISTS direct_messages (
                message_id TEXT PRIMARY KEY,
                chat_id TEXT NOT NULL,
                sender_id TEXT NOT NULL,
                username TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                is_deleted INTEGER NOT NULL DEFAULT 0,
                deleted_at TEXT NOT NULL DEFAULT '',
                deleted_by TEXT NOT NULL DEFAULT ''
            )
        """)

        await ensure_column(
            db,
            "direct_messages",
            "is_deleted",
            "is_deleted INTEGER NOT NULL DEFAULT 0",
        )

        await ensure_column(
            db,
            "direct_messages",
            "deleted_at",
            "deleted_at TEXT NOT NULL DEFAULT ''",
        )

        await ensure_column(
            db,
            "direct_messages",
            "deleted_by",
            "deleted_by TEXT NOT NULL DEFAULT ''",
        )

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_direct_chats_is_deleted
            ON direct_chats(is_deleted)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_direct_messages_chat
            ON direct_messages(chat_id)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_direct_messages_created_at
            ON direct_messages(created_at)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_direct_messages_is_deleted
            ON direct_messages(is_deleted)
        """)

        await db.commit()


def make_direct_chat_id(my_node_id, peer_node_id):
    if not my_node_id or not peer_node_id:
        raise ValueError("my_node_id and peer_node_id are required")

    ids = sorted([my_node_id, peer_node_id])
    return "direct_" + "_".join(ids)


async def save_direct_chat(chat):
    if not isinstance(chat, dict):
        return False

    chat_id = chat.get("chat_id", "")

    if not chat_id:
        return False

    incoming_is_deleted = 1 if chat.get("is_deleted") else 0
    incoming_deleted_at = chat.get("deleted_at") or ""
    incoming_deleted_by = chat.get("deleted_by") or ""

    async with aiosqlite.connect(DIRECT_DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO direct_chats
            (
                chat_id,
                peer_id,
                peer_name,
                created_at,
                is_deleted,
                deleted_at,
                deleted_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                peer_id = CASE
                    WHEN excluded.peer_id != '' THEN excluded.peer_id
                    ELSE direct_chats.peer_id
                END,

                peer_name = CASE
                    WHEN excluded.peer_name != '' THEN excluded.peer_name
                    ELSE direct_chats.peer_name
                END,

                created_at = CASE
                    WHEN excluded.created_at != '' THEN excluded.created_at
                    ELSE direct_chats.created_at
                END,

                is_deleted = CASE
                    WHEN direct_chats.is_deleted = 1 OR excluded.is_deleted = 1 THEN 1
                    ELSE 0
                END,

                deleted_at = CASE
                    WHEN excluded.deleted_at != '' THEN excluded.deleted_at
                    ELSE direct_chats.deleted_at
                END,

                deleted_by = CASE
                    WHEN excluded.deleted_by != '' THEN excluded.deleted_by
                    ELSE direct_chats.deleted_by
                END
        """, (
            chat_id,
            chat.get("peer_id", ""),
            chat.get("peer_name", ""),
            chat.get("created_at") or now_str(),
            incoming_is_deleted,
            incoming_deleted_at,
            incoming_deleted_by,
        ))

        changed = cursor.rowcount > 0

        await cursor.close()
        await db.commit()

        return changed


async def get_direct_chat(chat_id, include_deleted=False):
    if not chat_id:
        return None

    async with aiosqlite.connect(DIRECT_DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        if include_deleted:
            cursor = await db.execute("""
                SELECT chat_id,
                       peer_id,
                       peer_name,
                       created_at,
                       is_deleted,
                       deleted_at,
                       deleted_by
                FROM direct_chats
                WHERE chat_id = ?
            """, (chat_id,))
        else:
            cursor = await db.execute("""
                SELECT chat_id,
                       peer_id,
                       peer_name,
                       created_at,
                       is_deleted,
                       deleted_at,
                       deleted_by
                FROM direct_chats
                WHERE chat_id = ?
                  AND is_deleted = 0
            """, (chat_id,))

        row = await cursor.fetchone()
        await cursor.close()

        if not row:
            return None

        return direct_chat_row_to_dict(row)


async def get_direct_chats():
    async with aiosqlite.connect(DIRECT_DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute("""
            SELECT dc.chat_id,
                   dc.peer_id,
                   dc.peer_name,
                   dc.created_at,
                   dc.is_deleted,
                   dc.deleted_at,
                   dc.deleted_by,
                   MAX(dm.created_at) AS last_message_time
            FROM direct_chats dc
            LEFT JOIN direct_messages dm ON dc.chat_id = dm.chat_id
            WHERE dc.is_deleted = 0
            GROUP BY dc.chat_id
            ORDER BY last_message_time DESC, dc.created_at DESC
        """)

        rows = await cursor.fetchall()
        await cursor.close()

        return [direct_chat_row_to_dict(row) for row in rows]


async def delete_direct_chat(chat_id, deleted_by):
    """
    Мягко удаляет личный чат.

    Сообщения физически остаются в БД.
    Чат скрывается из списка через is_deleted = 1.
    """

    if not chat_id:
        return {
            "ok": False,
            "error": "empty_chat_id",
        }

    chat = await get_direct_chat(chat_id, include_deleted=True)

    if not chat:
        return {
            "ok": False,
            "error": "chat_not_found",
        }

    if chat.get("is_deleted"):
        return {
            "ok": True,
            "chat": chat,
        }

    deleted_at = now_str()

    async with aiosqlite.connect(DIRECT_DB_PATH) as db:
        cursor = await db.execute("""
            UPDATE direct_chats
            SET is_deleted = 1,
                deleted_at = ?,
                deleted_by = ?
            WHERE chat_id = ?
              AND is_deleted = 0
        """, (
            deleted_at,
            deleted_by or "",
            chat_id,
        ))

        changed = cursor.rowcount > 0

        await cursor.close()
        await db.commit()

    if not changed:
        return {
            "ok": False,
            "error": "delete_failed",
        }

    deleted_chat = await get_direct_chat(chat_id, include_deleted=True)

    return {
        "ok": True,
        "chat": deleted_chat,
    }


async def apply_direct_chat_delete(data):
    """
    Применяет P2P-удаление личного чата.
    """

    if not isinstance(data, dict):
        return {
            "ok": False,
            "error": "bad_data",
        }

    chat_id = data.get("chat_id", "")
    deleted_by = data.get("deleted_by", "")
    deleted_at = data.get("deleted_at") or now_str()

    if not chat_id:
        return {
            "ok": False,
            "error": "empty_chat_id",
        }

    chat = await get_direct_chat(chat_id, include_deleted=True)

    if not chat:
        # Если чата нет, но прилетел tombstone, сохраняем его,
        # чтобы не восстановить чат обратно при старом sync.
        tombstone = {
            "chat_id": chat_id,
            "peer_id": data.get("peer_id", ""),
            "peer_name": data.get("peer_name", ""),
            "created_at": data.get("created_at") or deleted_at,
            "is_deleted": True,
            "deleted_at": deleted_at,
            "deleted_by": deleted_by,
        }

        await save_direct_chat(tombstone)

        return {
            "ok": True,
            "chat": await get_direct_chat(chat_id, include_deleted=True),
        }

    if chat.get("is_deleted"):
        return {
            "ok": True,
            "chat": chat,
        }

    async with aiosqlite.connect(DIRECT_DB_PATH) as db:
        cursor = await db.execute("""
            UPDATE direct_chats
            SET is_deleted = 1,
                deleted_at = ?,
                deleted_by = ?
            WHERE chat_id = ?
              AND is_deleted = 0
        """, (
            deleted_at,
            deleted_by or "",
            chat_id,
        ))

        changed = cursor.rowcount > 0

        await cursor.close()
        await db.commit()

    if not changed:
        return {
            "ok": False,
            "error": "delete_failed",
        }

    return {
        "ok": True,
        "chat": await get_direct_chat(chat_id, include_deleted=True),
    }


async def save_direct_message(msg):
    async with aiosqlite.connect(DIRECT_DB_PATH) as db:
        cursor = await db.execute("""
            INSERT OR IGNORE INTO direct_messages
            (
                message_id,
                chat_id,
                sender_id,
                username,
                message,
                created_at,
                is_deleted,
                deleted_at,
                deleted_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            msg.get("message_id") or str(uuid.uuid4()),
            msg["chat_id"],
            msg["sender_id"],
            msg["username"],
            msg["message"],
            msg.get("created_at") or now_str(),
            1 if msg.get("is_deleted") else 0,
            msg.get("deleted_at") or "",
            msg.get("deleted_by") or "",
        ))

        changed = cursor.rowcount > 0

        await cursor.close()
        await db.commit()

        return changed


async def get_direct_message(message_id, include_deleted=True, mask_deleted=True):
    if not message_id:
        return None

    async with aiosqlite.connect(DIRECT_DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        if include_deleted:
            cursor = await db.execute("""
                SELECT message_id,
                       chat_id,
                       sender_id,
                       username,
                       message,
                       created_at,
                       is_deleted,
                       deleted_at,
                       deleted_by
                FROM direct_messages
                WHERE message_id = ?
            """, (message_id,))
        else:
            cursor = await db.execute("""
                SELECT message_id,
                       chat_id,
                       sender_id,
                       username,
                       message,
                       created_at,
                       is_deleted,
                       deleted_at,
                       deleted_by
                FROM direct_messages
                WHERE message_id = ?
                  AND is_deleted = 0
            """, (message_id,))

        row = await cursor.fetchone()
        await cursor.close()

        if not row:
            return None

        return direct_message_row_to_dict(row, mask_deleted=mask_deleted)


async def get_direct_messages(chat_id=None):
    async with aiosqlite.connect(DIRECT_DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        if chat_id:
            chat = await get_direct_chat(chat_id)

            if not chat:
                return []

            cursor = await db.execute("""
                SELECT message_id,
                       chat_id,
                       sender_id,
                       username,
                       message,
                       created_at,
                       is_deleted,
                       deleted_at,
                       deleted_by
                FROM direct_messages
                WHERE chat_id = ?
                ORDER BY created_at ASC
            """, (chat_id,))
        else:
            cursor = await db.execute("""
                SELECT dm.message_id,
                       dm.chat_id,
                       dm.sender_id,
                       dm.username,
                       dm.message,
                       dm.created_at,
                       dm.is_deleted,
                       dm.deleted_at,
                       dm.deleted_by
                FROM direct_messages dm
                INNER JOIN direct_chats dc ON dm.chat_id = dc.chat_id
                WHERE dc.is_deleted = 0
                ORDER BY dm.created_at ASC
            """)

        rows = await cursor.fetchall()
        await cursor.close()

        return [
            direct_message_row_to_dict(row, mask_deleted=True)
            for row in rows
        ]


async def delete_direct_message(message_id, chat_id, deleted_by):
    if not message_id:
        return {
            "ok": False,
            "error": "empty_message_id",
        }

    if not chat_id:
        return {
            "ok": False,
            "error": "empty_chat_id",
        }

    chat = await get_direct_chat(chat_id)

    if not chat:
        return {
            "ok": False,
            "error": "chat_not_found",
        }

    message = await get_direct_message(
        message_id,
        include_deleted=True,
        mask_deleted=False,
    )

    if not message:
        return {
            "ok": False,
            "error": "message_not_found",
        }

    if message.get("chat_id") != chat_id:
        return {
            "ok": False,
            "error": "wrong_chat",
        }

    if message.get("is_deleted"):
        return {
            "ok": True,
            "message": await get_direct_message(message_id, mask_deleted=True),
        }

    if message.get("sender_id") != deleted_by:
        return {
            "ok": False,
            "error": "not_sender",
        }

    deleted_at = now_str()

    async with aiosqlite.connect(DIRECT_DB_PATH) as db:
        cursor = await db.execute("""
            UPDATE direct_messages
            SET is_deleted = 1,
                deleted_at = ?,
                deleted_by = ?
            WHERE message_id = ?
              AND chat_id = ?
              AND sender_id = ?
              AND is_deleted = 0
        """, (
            deleted_at,
            deleted_by,
            message_id,
            chat_id,
            deleted_by,
        ))

        changed = cursor.rowcount > 0

        await cursor.close()
        await db.commit()

    if not changed:
        return {
            "ok": False,
            "error": "delete_failed",
        }

    deleted_message = await get_direct_message(
        message_id,
        include_deleted=True,
        mask_deleted=True,
    )

    return {
        "ok": True,
        "message": deleted_message,
    }


async def apply_direct_message_delete(data):
    if not isinstance(data, dict):
        return {
            "ok": False,
            "error": "bad_data",
        }

    message_id = data.get("message_id", "")
    chat_id = data.get("chat_id", "")
    deleted_by = data.get("deleted_by", "")

    if not message_id:
        return {
            "ok": False,
            "error": "empty_message_id",
        }

    if not chat_id:
        return {
            "ok": False,
            "error": "empty_chat_id",
        }

    if not deleted_by:
        return {
            "ok": False,
            "error": "empty_deleted_by",
        }

    message = await get_direct_message(
        message_id,
        include_deleted=True,
        mask_deleted=False,
    )

    if not message:
        return {
            "ok": False,
            "error": "message_not_found",
        }

    if message.get("chat_id") != chat_id:
        return {
            "ok": False,
            "error": "wrong_chat",
        }

    if message.get("sender_id") != deleted_by:
        return {
            "ok": False,
            "error": "not_sender",
        }

    if message.get("is_deleted"):
        return {
            "ok": True,
            "message": await get_direct_message(message_id, mask_deleted=True),
        }

    deleted_at = data.get("deleted_at") or now_str()

    async with aiosqlite.connect(DIRECT_DB_PATH) as db:
        cursor = await db.execute("""
            UPDATE direct_messages
            SET is_deleted = 1,
                deleted_at = ?,
                deleted_by = ?
            WHERE message_id = ?
              AND chat_id = ?
              AND sender_id = ?
              AND is_deleted = 0
        """, (
            deleted_at,
            deleted_by,
            message_id,
            chat_id,
            deleted_by,
        ))

        changed = cursor.rowcount > 0

        await cursor.close()
        await db.commit()

    if not changed:
        return {
            "ok": False,
            "error": "delete_failed",
        }

    deleted_message = await get_direct_message(
        message_id,
        include_deleted=True,
        mask_deleted=True,
    )

    return {
        "ok": True,
        "message": deleted_message,
    }
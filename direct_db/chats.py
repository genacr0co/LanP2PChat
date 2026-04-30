import aiosqlite

from settings import DIRECT_DB_PATH

from .common import now_str, direct_chat_row_to_dict


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
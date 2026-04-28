import aiosqlite

from settings import GROUPS_DB_PATH

from .common import now_str, group_message_row_to_dict
from .groups import get_group


async def save_group_message(data):
    if not isinstance(data, dict):
        return False

    room_id = data.get("room_id") or "general"

    if room_id.startswith("dm_") or room_id.startswith("direct_"):
        return False

    group = await get_group(room_id)

    if not group:
        return False

    if not group.get("is_joined"):
        return False

    async with aiosqlite.connect(GROUPS_DB_PATH) as db:
        cursor = await db.execute("""
            INSERT OR IGNORE INTO group_messages
            (
                message_id,
                room_id,
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
            data["message_id"],
            room_id,
            data["sender_id"],
            data["username"],
            data.get("message", ""),
            data["created_at"],
            1 if data.get("is_deleted") else 0,
            data.get("deleted_at") or "",
            data.get("deleted_by") or "",
        ))

        changed = cursor.rowcount > 0

        await cursor.close()
        await db.commit()

        return changed


async def get_group_message(message_id, include_deleted=True, mask_deleted=True):
    if not message_id:
        return None

    async with aiosqlite.connect(GROUPS_DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        if include_deleted:
            cursor = await db.execute("""
                SELECT message_id,
                       room_id,
                       sender_id,
                       username,
                       message,
                       created_at,
                       is_deleted,
                       deleted_at,
                       deleted_by
                FROM group_messages
                WHERE message_id = ?
            """, (message_id,))
        else:
            cursor = await db.execute("""
                SELECT message_id,
                       room_id,
                       sender_id,
                       username,
                       message,
                       created_at,
                       is_deleted,
                       deleted_at,
                       deleted_by
                FROM group_messages
                WHERE message_id = ?
                  AND is_deleted = 0
            """, (message_id,))

        row = await cursor.fetchone()
        await cursor.close()

        if not row:
            return None

        return group_message_row_to_dict(row, mask_deleted=mask_deleted)


async def get_group_messages(room_id=None):
    async with aiosqlite.connect(GROUPS_DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        if room_id:
            group = await get_group(room_id)

            if not group or not group.get("is_joined"):
                return []

            cursor = await db.execute("""
                SELECT message_id,
                       room_id,
                       sender_id,
                       username,
                       message,
                       created_at,
                       is_deleted,
                       deleted_at,
                       deleted_by
                FROM group_messages
                WHERE room_id = ?
                ORDER BY created_at ASC
            """, (room_id,))
        else:
            cursor = await db.execute("""
                SELECT gm.message_id,
                       gm.room_id,
                       gm.sender_id,
                       gm.username,
                       gm.message,
                       gm.created_at,
                       gm.is_deleted,
                       gm.deleted_at,
                       gm.deleted_by
                FROM group_messages gm
                INNER JOIN groups g ON gm.room_id = g.room_id
                WHERE g.is_joined = 1
                  AND g.is_deleted = 0
                ORDER BY gm.created_at ASC
            """)

        rows = await cursor.fetchall()
        await cursor.close()

        return [
            group_message_row_to_dict(row, mask_deleted=True)
            for row in rows
        ]


async def delete_group_message(message_id, room_id, deleted_by):
    if not message_id:
        return {
            "ok": False,
            "error": "empty_message_id",
        }

    if not room_id:
        return {
            "ok": False,
            "error": "empty_room_id",
        }

    group = await get_group(room_id)

    if not group:
        return {
            "ok": False,
            "error": "group_not_found",
        }

    if not group.get("is_joined"):
        return {
            "ok": False,
            "error": "not_joined",
        }

    message = await get_group_message(
        message_id,
        include_deleted=True,
        mask_deleted=False,
    )

    if not message:
        return {
            "ok": False,
            "error": "message_not_found",
        }

    if message.get("room_id") != room_id:
        return {
            "ok": False,
            "error": "wrong_room",
        }

    if message.get("is_deleted"):
        return {
            "ok": True,
            "message": await get_group_message(message_id, mask_deleted=True),
        }

    if message.get("sender_id") != deleted_by:
        return {
            "ok": False,
            "error": "not_sender",
        }

    deleted_at = now_str()

    async with aiosqlite.connect(GROUPS_DB_PATH) as db:
        cursor = await db.execute("""
            UPDATE group_messages
            SET is_deleted = 1,
                deleted_at = ?,
                deleted_by = ?
            WHERE message_id = ?
              AND room_id = ?
              AND sender_id = ?
              AND is_deleted = 0
        """, (
            deleted_at,
            deleted_by,
            message_id,
            room_id,
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

    deleted_message = await get_group_message(
        message_id,
        include_deleted=True,
        mask_deleted=True,
    )

    return {
        "ok": True,
        "message": deleted_message,
    }


async def apply_group_message_delete(data):
    if not isinstance(data, dict):
        return {
            "ok": False,
            "error": "bad_data",
        }

    message_id = data.get("message_id", "")
    room_id = data.get("room_id", "")
    deleted_by = data.get("deleted_by", "")

    if not message_id:
        return {
            "ok": False,
            "error": "empty_message_id",
        }

    if not room_id:
        return {
            "ok": False,
            "error": "empty_room_id",
        }

    if not deleted_by:
        return {
            "ok": False,
            "error": "empty_deleted_by",
        }

    message = await get_group_message(
        message_id,
        include_deleted=True,
        mask_deleted=False,
    )

    if not message:
        return {
            "ok": False,
            "error": "message_not_found",
        }

    if message.get("room_id") != room_id:
        return {
            "ok": False,
            "error": "wrong_room",
        }

    if message.get("sender_id") != deleted_by:
        return {
            "ok": False,
            "error": "not_sender",
        }

    if message.get("is_deleted"):
        return {
            "ok": True,
            "message": await get_group_message(message_id, mask_deleted=True),
        }

    deleted_at = data.get("deleted_at") or now_str()

    async with aiosqlite.connect(GROUPS_DB_PATH) as db:
        cursor = await db.execute("""
            UPDATE group_messages
            SET is_deleted = 1,
                deleted_at = ?,
                deleted_by = ?
            WHERE message_id = ?
              AND room_id = ?
              AND sender_id = ?
              AND is_deleted = 0
        """, (
            deleted_at,
            deleted_by,
            message_id,
            room_id,
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

    deleted_message = await get_group_message(
        message_id,
        include_deleted=True,
        mask_deleted=True,
    )

    return {
        "ok": True,
        "message": deleted_message,
    }
import aiosqlite

from settings import GROUPS_DB_PATH

from .common import now_str, group_message_row_to_dict
from .groups import get_group


DEFAULT_MESSAGES_LIMIT = 40
MAX_MESSAGES_LIMIT = 100


def normalize_limit(limit):
    try:
        value = int(limit)
    except Exception:
        value = DEFAULT_MESSAGES_LIMIT

    if value <= 0:
        return DEFAULT_MESSAGES_LIMIT

    return min(value, MAX_MESSAGES_LIMIT)


def build_messages_page(rows, limit):
    """
    rows приходят из SQL в DESC-порядке.
    Для фронта отдаём ASC-порядок: старые сверху, новые снизу.
    """

    has_more = len(rows) > limit

    rows = rows[:limit]
    rows = list(reversed(rows))

    items = [
        group_message_row_to_dict(row, mask_deleted=True)
        for row in rows
    ]

    next_before_created_at = None
    next_before_message_id = None

    if items:
        oldest = items[0]
        next_before_created_at = oldest.get("created_at")
        next_before_message_id = oldest.get("message_id")

    return {
        "items": items,
        "has_more": has_more,
        "next_before_created_at": next_before_created_at,
        "next_before_message_id": next_before_message_id,
    }


async def group_message_duplicate_exists(
    db,
    room_id,
    sender_id,
    username,
    message,
    created_at,
):
    cursor = await db.execute("""
        SELECT message_id
        FROM group_messages
        WHERE room_id = ?
          AND sender_id = ?
          AND username = ?
          AND message = ?
          AND created_at = ?
        LIMIT 1
    """, (
        room_id,
        sender_id,
        username,
        message,
        created_at,
    ))

    row = await cursor.fetchone()
    await cursor.close()

    return row is not None


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

    message_id = data.get("message_id", "")
    sender_id = data.get("sender_id", "")
    username = data.get("username", "")
    message = data.get("message", "")
    created_at = data.get("created_at", "")

    if not message_id:
        return False

    if not sender_id:
        return False

    if not created_at:
        return False

    async with aiosqlite.connect(GROUPS_DB_PATH) as db:
        duplicate_exists = await group_message_duplicate_exists(
            db=db,
            room_id=room_id,
            sender_id=sender_id,
            username=username,
            message=message,
            created_at=created_at,
        )

        if duplicate_exists:
            return False

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
            message_id,
            room_id,
            sender_id,
            username,
            message,
            created_at,
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
    """
    Старый метод оставляем для совместимости:
    - sync пока может использовать полный список;
    - старый frontend тоже не сломается.
    """

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
                ORDER BY created_at ASC, message_id ASC
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
                ORDER BY gm.created_at ASC, gm.message_id ASC
            """)

        rows = await cursor.fetchall()
        await cursor.close()

        return [
            group_message_row_to_dict(row, mask_deleted=True)
            for row in rows
        ]


async def get_group_messages_page(
    room_id,
    limit=DEFAULT_MESSAGES_LIMIT,
    before_created_at=None,
    before_message_id=None,
):
    """
    Пагинация сообщений группы.

    Логика как в Telegram:
    - первый запрос без before_* возвращает последние сообщения;
    - при скролле вверх фронт передаёт курсор самого старого сообщения;
    - возвращаем более старые сообщения;
    - items всегда в ASC-порядке для нормального рендера.
    """

    if not room_id:
        return {
            "items": [],
            "has_more": False,
            "next_before_created_at": None,
            "next_before_message_id": None,
        }

    group = await get_group(room_id)

    if not group or not group.get("is_joined"):
        return {
            "items": [],
            "has_more": False,
            "next_before_created_at": None,
            "next_before_message_id": None,
        }

    page_limit = normalize_limit(limit)
    sql_limit = page_limit + 1

    has_cursor = bool(before_created_at and before_message_id)

    async with aiosqlite.connect(GROUPS_DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        if has_cursor:
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
                  AND (
                        created_at < ?
                        OR (
                            created_at = ?
                            AND message_id < ?
                        )
                  )
                ORDER BY created_at DESC, message_id DESC
                LIMIT ?
            """, (
                room_id,
                before_created_at,
                before_created_at,
                before_message_id,
                sql_limit,
            ))
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
                WHERE room_id = ?
                ORDER BY created_at DESC, message_id DESC
                LIMIT ?
            """, (
                room_id,
                sql_limit,
            ))

        rows = await cursor.fetchall()
        await cursor.close()

    return build_messages_page(rows, page_limit)


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
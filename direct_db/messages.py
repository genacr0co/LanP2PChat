import uuid

import aiosqlite

from settings import DIRECT_DB_PATH

from .common import now_str, direct_message_row_to_dict
from .chats import get_direct_chat


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
        direct_message_row_to_dict(row, mask_deleted=True)
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


async def direct_message_duplicate_exists(
    db,
    chat_id,
    sender_id,
    username,
    message,
    created_at,
):
    cursor = await db.execute("""
        SELECT message_id
        FROM direct_messages
        WHERE chat_id = ?
          AND sender_id = ?
          AND username = ?
          AND message = ?
          AND created_at = ?
        LIMIT 1
    """, (
        chat_id,
        sender_id,
        username,
        message,
        created_at,
    ))

    row = await cursor.fetchone()
    await cursor.close()

    return row is not None


async def save_direct_message(msg):
    if not isinstance(msg, dict):
        return False

    message_id = msg.get("message_id") or str(uuid.uuid4())
    chat_id = msg.get("chat_id", "")
    sender_id = msg.get("sender_id", "")
    username = msg.get("username", "")
    message = msg.get("message", "")
    created_at = msg.get("created_at") or now_str()

    if not message_id:
        return False

    if not chat_id:
        return False

    if not sender_id:
        return False

    if not created_at:
        return False

    async with aiosqlite.connect(DIRECT_DB_PATH) as db:
        duplicate_exists = await direct_message_duplicate_exists(
            db=db,
            chat_id=chat_id,
            sender_id=sender_id,
            username=username,
            message=message,
            created_at=created_at,
        )

        if duplicate_exists:
            return False

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
            message_id,
            chat_id,
            sender_id,
            username,
            message,
            created_at,
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
    """
    Старый метод оставляем:
    - direct sync пока может использовать полный список;
    - старый frontend тоже не сломается.
    """

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
                ORDER BY created_at ASC, message_id ASC
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
                ORDER BY dm.created_at ASC, dm.message_id ASC
            """)

        rows = await cursor.fetchall()
        await cursor.close()

        return [
            direct_message_row_to_dict(row, mask_deleted=True)
            for row in rows
        ]


async def get_direct_messages_page(
    chat_id,
    limit=DEFAULT_MESSAGES_LIMIT,
    before_created_at=None,
    before_message_id=None,
):
    """
    Пагинация личных сообщений.

    Логика как в Telegram:
    - первый запрос без before_* возвращает последние сообщения;
    - при скролле вверх фронт передаёт курсор самого старого сообщения;
    - возвращаем более старые сообщения;
    - items всегда в ASC-порядке для нормального рендера.
    """

    if not chat_id:
        return {
            "items": [],
            "has_more": False,
            "next_before_created_at": None,
            "next_before_message_id": None,
        }

    chat = await get_direct_chat(chat_id)

    if not chat:
        return {
            "items": [],
            "has_more": False,
            "next_before_created_at": None,
            "next_before_message_id": None,
        }

    page_limit = normalize_limit(limit)
    sql_limit = page_limit + 1

    has_cursor = bool(before_created_at and before_message_id)

    async with aiosqlite.connect(DIRECT_DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        if has_cursor:
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
                chat_id,
                before_created_at,
                before_created_at,
                before_message_id,
                sql_limit,
            ))
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
                WHERE chat_id = ?
                ORDER BY created_at DESC, message_id DESC
                LIMIT ?
            """, (
                chat_id,
                sql_limit,
            ))

        rows = await cursor.fetchall()
        await cursor.close()

    return build_messages_page(rows, page_limit)


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
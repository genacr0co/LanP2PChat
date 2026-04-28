import uuid

import aiosqlite

from settings import GROUPS_DB_PATH

from .common import now_str, group_row_to_dict


async def create_group(name, password="", created_by="", unique_name=""):
    room_id = str(uuid.uuid4())

    if not unique_name:
        unique_name = name.strip().lower()

    group = {
        "room_id": room_id,
        "name": name,
        "unique_name": unique_name,
        "password_hash": "",
        "created_by": created_by,
        "created_at": now_str(),
        "is_creator": True,
        "is_joined": True,
        "has_password": False,
        "is_deleted": False,
        "deleted_at": "",
        "deleted_by": "",
    }

    await save_group(group)

    return group


async def save_group(group):
    if not isinstance(group, dict):
        return False

    room_id = group.get("room_id", "")

    if not room_id:
        return False

    if room_id.startswith("dm_") or room_id.startswith("direct_"):
        return False

    name = str(group.get("name", "")).strip()

    if not name:
        return False

    incoming_is_deleted = 1 if group.get("is_deleted") else 0
    incoming_deleted_at = group.get("deleted_at") or ""
    incoming_deleted_by = group.get("deleted_by") or ""

    if room_id == "general":
        incoming_is_deleted = 0
        incoming_deleted_at = ""
        incoming_deleted_by = ""

    async with aiosqlite.connect(GROUPS_DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO groups
            (
                room_id,
                name,
                unique_name,
                password_hash,
                created_by,
                created_at,
                is_creator,
                is_joined,
                has_password,
                is_deleted,
                deleted_at,
                deleted_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(room_id) DO UPDATE SET
                name = CASE
                    WHEN excluded.is_deleted = 1 THEN groups.name
                    ELSE excluded.name
                END,

                unique_name = CASE
                    WHEN excluded.unique_name != '' THEN excluded.unique_name
                    ELSE groups.unique_name
                END,

                password_hash = '',

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
                    WHEN excluded.is_deleted = 1 THEN 0
                    WHEN groups.is_joined = 1 OR excluded.is_joined = 1 THEN 1
                    ELSE 0
                END,

                has_password = 0,

                is_deleted = CASE
                    WHEN groups.room_id = 'general' THEN 0
                    WHEN groups.is_deleted = 1 OR excluded.is_deleted = 1 THEN 1
                    ELSE 0
                END,

                deleted_at = CASE
                    WHEN groups.room_id = 'general' THEN ''
                    WHEN excluded.deleted_at != '' THEN excluded.deleted_at
                    ELSE groups.deleted_at
                END,

                deleted_by = CASE
                    WHEN groups.room_id = 'general' THEN ''
                    WHEN excluded.deleted_by != '' THEN excluded.deleted_by
                    ELSE groups.deleted_by
                END
        """, (
            room_id,
            name,
            group.get("unique_name", ""),
            "",
            group.get("created_by", ""),
            group.get("created_at") or now_str(),
            1 if group.get("is_creator") else 0,
            1 if group.get("is_joined") else 0,
            0,
            incoming_is_deleted,
            incoming_deleted_at,
            incoming_deleted_by,
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

    if room_id == "general":
        return False

    existing = await get_group(room_id, include_deleted=True)

    if existing:
        return False

    discovered = {
        "room_id": room_id,
        "name": group.get("name", ""),
        "unique_name": group.get("unique_name", ""),
        "password_hash": "",
        "created_by": group.get("created_by", ""),
        "created_at": group.get("created_at") or now_str(),
        "is_creator": False,
        "is_joined": False,
        "has_password": False,
        "is_deleted": bool(group.get("is_deleted")),
        "deleted_at": group.get("deleted_at") or "",
        "deleted_by": group.get("deleted_by") or "",
    }

    return await save_group(discovered)


async def join_group(room_id):
    if not room_id:
        return False

    if room_id == "general":
        return True

    async with aiosqlite.connect(GROUPS_DB_PATH) as db:
        cursor = await db.execute("""
            UPDATE groups
            SET is_joined = 1,
                has_password = 0,
                password_hash = ''
            WHERE room_id = ?
              AND is_deleted = 0
        """, (room_id,))

        changed = cursor.rowcount > 0

        await cursor.close()
        await db.commit()

        return changed


async def leave_group(room_id):
    """
    Локальный выход из группы.

    Важно:
    - общий чат покинуть нельзя;
    - группу не удаляем;
    - creator остаётся creator;
    - is_joined становится 0;
    - пользователь сможет потом снова вступить.
    """

    if not room_id:
        return {
            "ok": False,
            "error": "empty_room_id",
        }

    if room_id == "general":
        return {
            "ok": False,
            "error": "cannot_leave_general",
        }

    group = await get_group(room_id, include_deleted=True)

    if not group:
        return {
            "ok": False,
            "error": "group_not_found",
        }

    if group.get("is_deleted"):
        return {
            "ok": False,
            "error": "group_deleted",
        }

    if not group.get("is_joined"):
        return {
            "ok": True,
            "room": group,
        }

    async with aiosqlite.connect(GROUPS_DB_PATH) as db:
        cursor = await db.execute("""
            UPDATE groups
            SET is_joined = 0,
                has_password = 0,
                password_hash = ''
            WHERE room_id = ?
              AND room_id != 'general'
              AND is_deleted = 0
        """, (room_id,))

        changed = cursor.rowcount > 0

        await cursor.close()
        await db.commit()

    if not changed:
        return {
            "ok": False,
            "error": "leave_failed",
        }

    return {
        "ok": True,
        "room": await get_group(room_id, include_deleted=True),
    }


async def delete_group(room_id, deleted_by):
    if not room_id:
        return {
            "ok": False,
            "error": "empty_room_id",
        }

    if room_id == "general":
        return {
            "ok": False,
            "error": "cannot_delete_general",
        }

    group = await get_group(room_id, include_deleted=True)

    if not group:
        return {
            "ok": False,
            "error": "group_not_found",
        }

    if group.get("is_deleted"):
        return {
            "ok": True,
            "room": group,
        }

    if not group.get("is_creator"):
        return {
            "ok": False,
            "error": "not_creator",
        }

    deleted_at = now_str()

    async with aiosqlite.connect(GROUPS_DB_PATH) as db:
        cursor = await db.execute("""
            UPDATE groups
            SET is_deleted = 1,
                deleted_at = ?,
                deleted_by = ?,
                is_joined = 0
            WHERE room_id = ?
              AND room_id != 'general'
              AND is_creator = 1
        """, (
            deleted_at,
            deleted_by or "",
            room_id,
        ))

        changed = cursor.rowcount > 0

        await cursor.close()
        await db.commit()

    if not changed:
        return {
            "ok": False,
            "error": "delete_failed",
        }

    deleted_group = await get_group(room_id, include_deleted=True)

    return {
        "ok": True,
        "room": deleted_group,
    }


async def rename_group(room_id, new_name, updated_by):
    if not room_id:
        return {
            "ok": False,
            "error": "empty_room_id",
        }

    if room_id == "general":
        return {
            "ok": False,
            "error": "cannot_rename_general",
        }

    new_name = str(new_name or "").strip()

    if not new_name:
        return {
            "ok": False,
            "error": "empty_name",
        }

    group = await get_group(room_id, include_deleted=True)

    if not group:
        return {
            "ok": False,
            "error": "group_not_found",
        }

    if group.get("is_deleted"):
        return {
            "ok": False,
            "error": "group_deleted",
        }

    if not group.get("is_creator"):
        return {
            "ok": False,
            "error": "not_creator",
        }

    async with aiosqlite.connect(GROUPS_DB_PATH) as db:
        cursor = await db.execute("""
            UPDATE groups
            SET name = ?,
                unique_name = ?
            WHERE room_id = ?
              AND room_id != 'general'
              AND is_creator = 1
              AND is_deleted = 0
        """, (
            new_name,
            new_name.lower(),
            room_id,
        ))

        changed = cursor.rowcount > 0

        await cursor.close()
        await db.commit()

    if not changed:
        return {
            "ok": False,
            "error": "rename_failed",
        }

    renamed_group = await get_group(room_id, include_deleted=True)

    return {
        "ok": True,
        "room": renamed_group,
    }


async def get_group(room_id, include_deleted=False):
    if not room_id:
        return None

    async with aiosqlite.connect(GROUPS_DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        if include_deleted:
            cursor = await db.execute("""
                SELECT room_id,
                       name,
                       unique_name,
                       password_hash,
                       created_by,
                       created_at,
                       is_creator,
                       is_joined,
                       has_password,
                       is_deleted,
                       deleted_at,
                       deleted_by
                FROM groups
                WHERE room_id = ?
            """, (room_id,))
        else:
            cursor = await db.execute("""
                SELECT room_id,
                       name,
                       unique_name,
                       password_hash,
                       created_by,
                       created_at,
                       is_creator,
                       is_joined,
                       has_password,
                       is_deleted,
                       deleted_at,
                       deleted_by
                FROM groups
                WHERE room_id = ?
                  AND is_deleted = 0
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
                SELECT room_id,
                       name,
                       unique_name,
                       password_hash,
                       created_by,
                       created_at,
                       is_creator,
                       is_joined,
                       has_password,
                       is_deleted,
                       deleted_at,
                       deleted_by
                FROM groups
                WHERE is_deleted = 0
                ORDER BY created_at ASC
            """)
        else:
            cursor = await db.execute("""
                SELECT room_id,
                       name,
                       unique_name,
                       password_hash,
                       created_by,
                       created_at,
                       is_creator,
                       is_joined,
                       has_password,
                       is_deleted,
                       deleted_at,
                       deleted_by
                FROM groups
                WHERE is_joined = 1
                  AND is_deleted = 0
                ORDER BY created_at ASC
            """)

        rows = await cursor.fetchall()
        await cursor.close()

        return [group_row_to_dict(row) for row in rows]


async def get_joined_groups():
    return await get_all_groups(include_not_joined=False)


async def check_group_password(room_id, password):
    group = await get_group(room_id)

    if not group:
        return False

    return True
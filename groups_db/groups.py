import hashlib
import uuid

import aiosqlite

from settings import GROUPS_DB_PATH

from .common import now_str, group_row_to_dict


GROUP_SELECT_COLUMNS = """
    room_id,
    name,
    unique_name,
    password_hash,
    password_version,
    unlocked_password_version,
    created_by,
    created_at,
    is_creator,
    is_joined,
    has_password,
    is_deleted,
    deleted_at,
    deleted_by
"""


def normalize_password(password):
    return str(password or "").strip()


def make_group_password_hash(room_id, password):
    """
    Пароль не храним открытым текстом.

    Для LAN-защиты достаточно локально сверять hash.
    room_id добавляем как salt, чтобы одинаковые пароли у разных групп
    не давали одинаковый password_hash.
    """
    password = normalize_password(password)

    if not room_id or not password:
        return ""

    raw = f"lanp2pchat-group-password-v1:{room_id}:{password}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


async def create_group(name, password="", created_by="", unique_name=""):
    room_id = str(uuid.uuid4())

    if not unique_name:
        unique_name = name.strip().lower()

    password = normalize_password(password)
    has_password = bool(password)
    password_version = 1 if has_password else 0
    password_hash = make_group_password_hash(room_id, password) if has_password else ""

    group = {
        "room_id": room_id,
        "name": name,
        "unique_name": unique_name,
        "password_hash": password_hash,
        "password_version": password_version,
        "unlocked_password_version": password_version,
        "created_by": created_by,
        "created_at": now_str(),
        "is_creator": True,
        "is_joined": True,
        "has_password": has_password,
        "is_deleted": False,
        "deleted_at": "",
        "deleted_by": "",
    }

    await save_group(group)

    return await get_group(room_id, include_password_hash=True) or group


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

    incoming_password_hash = str(group.get("password_hash") or "")
    incoming_has_password = 1 if group.get("has_password") else 0
    incoming_password_version = _safe_int(group.get("password_version"), 0)
    incoming_unlocked_password_version = _safe_int(
        group.get("unlocked_password_version"),
        0,
    )

    if incoming_has_password and not incoming_password_hash:
        incoming_has_password = 0
        incoming_password_version = 0

    if room_id == "general":
        incoming_is_deleted = 0
        incoming_deleted_at = ""
        incoming_deleted_by = ""
        incoming_password_hash = ""
        incoming_has_password = 0
        incoming_password_version = 0
        incoming_unlocked_password_version = 0

    async with aiosqlite.connect(GROUPS_DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO groups
            (
                room_id,
                name,
                unique_name,
                password_hash,
                password_version,
                unlocked_password_version,
                created_by,
                created_at,
                is_creator,
                is_joined,
                has_password,
                is_deleted,
                deleted_at,
                deleted_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(room_id) DO UPDATE SET
                name = CASE
                    WHEN excluded.is_deleted = 1 THEN groups.name
                    ELSE excluded.name
                END,

                unique_name = CASE
                    WHEN excluded.unique_name != '' THEN excluded.unique_name
                    ELSE groups.unique_name
                END,

                password_hash = CASE
                    WHEN groups.room_id = 'general' THEN ''
                    WHEN excluded.password_version > groups.password_version THEN excluded.password_hash
                    WHEN groups.password_hash = '' AND excluded.password_hash != '' THEN excluded.password_hash
                    ELSE groups.password_hash
                END,

                password_version = CASE
                    WHEN groups.room_id = 'general' THEN 0
                    WHEN excluded.password_version > groups.password_version THEN excluded.password_version
                    WHEN groups.password_version = 0 AND excluded.password_version > 0 THEN excluded.password_version
                    ELSE groups.password_version
                END,

                unlocked_password_version = CASE
                    WHEN groups.room_id = 'general' THEN 0
                    WHEN groups.is_creator = 1 THEN
                        CASE
                            WHEN excluded.password_version > groups.password_version THEN excluded.password_version
                            ELSE groups.unlocked_password_version
                        END
                    WHEN excluded.unlocked_password_version > groups.unlocked_password_version THEN excluded.unlocked_password_version
                    ELSE groups.unlocked_password_version
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
                    WHEN excluded.is_deleted = 1 THEN 0
                    WHEN groups.is_joined = 1 OR excluded.is_joined = 1 THEN 1
                    ELSE 0
                END,

                has_password = CASE
                    WHEN groups.room_id = 'general' THEN 0
                    WHEN excluded.password_version > groups.password_version THEN excluded.has_password
                    WHEN groups.has_password = 1 OR excluded.has_password = 1 THEN 1
                    ELSE 0
                END,

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
            incoming_password_hash,
            incoming_password_version,
            incoming_unlocked_password_version,
            group.get("created_by", ""),
            group.get("created_at") or now_str(),
            1 if group.get("is_creator") else 0,
            1 if group.get("is_joined") else 0,
            incoming_has_password,
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

    password_hash = str(group.get("password_hash") or "")
    password_version = _safe_int(group.get("password_version"), 0)
    has_password = bool(group.get("has_password")) and bool(password_hash)

    if not has_password:
        password_hash = ""
        password_version = 0

    discovered = {
        "room_id": room_id,
        "name": group.get("name", ""),
        "unique_name": group.get("unique_name", ""),
        "password_hash": password_hash,
        "password_version": password_version,
        "unlocked_password_version": 0,
        "created_by": group.get("created_by", ""),
        "created_at": group.get("created_at") or now_str(),
        "is_creator": False,
        "is_joined": False,
        "has_password": has_password,
        "is_deleted": bool(group.get("is_deleted")),
        "deleted_at": group.get("deleted_at") or "",
        "deleted_by": group.get("deleted_by") or "",
    }

    return await save_group(discovered)


async def join_group(room_id, password=""):
    if not room_id:
        return False

    if room_id == "general":
        return True

    group = await get_group(room_id, include_password_hash=True)

    if not group:
        return False

    if group.get("is_deleted"):
        return False

    password_version = _safe_int(group.get("password_version"), 0)
    unlocked_password_version = _safe_int(
        group.get("unlocked_password_version"),
        0,
    )

    if group.get("has_password"):
        if unlocked_password_version < password_version:
            if not check_group_password_value(group, password):
                return False

            unlocked_password_version = password_version
    else:
        unlocked_password_version = 0

    async with aiosqlite.connect(GROUPS_DB_PATH) as db:
        cursor = await db.execute("""
            UPDATE groups
            SET is_joined = 1,
                unlocked_password_version = ?
            WHERE room_id = ?
              AND is_deleted = 0
        """, (
            unlocked_password_version,
            room_id,
        ))

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
    - локальная разблокировка пароля остаётся, пока пароль не поменяли;
    - пользователь сможет потом снова вступить без повторного ввода пароля,
      если password_version не изменился.
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
            SET is_joined = 0
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


async def update_group_password(room_id, password, updated_by):
    if not room_id:
        return {
            "ok": False,
            "error": "empty_room_id",
        }

    if room_id == "general":
        return {
            "ok": False,
            "error": "cannot_change_general_password",
        }

    group = await get_group(room_id, include_deleted=True, include_password_hash=True)

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

    password = normalize_password(password)
    has_password = bool(password)
    old_version = _safe_int(group.get("password_version"), 0)
    new_version = old_version + 1

    if has_password:
        password_hash = make_group_password_hash(room_id, password)
        unlocked_password_version = new_version
    else:
        password_hash = ""
        unlocked_password_version = 0

    async with aiosqlite.connect(GROUPS_DB_PATH) as db:
        cursor = await db.execute("""
            UPDATE groups
            SET password_hash = ?,
                password_version = ?,
                unlocked_password_version = ?,
                has_password = ?
            WHERE room_id = ?
              AND room_id != 'general'
              AND is_creator = 1
              AND is_deleted = 0
        """, (
            password_hash,
            new_version,
            unlocked_password_version,
            1 if has_password else 0,
            room_id,
        ))

        changed = cursor.rowcount > 0

        await cursor.close()
        await db.commit()

    if not changed:
        return {
            "ok": False,
            "error": "password_update_failed",
        }

    updated_group = await get_group(room_id, include_deleted=True, include_password_hash=True)

    return {
        "ok": True,
        "room": updated_group,
    }


def check_group_password_value(group, password):
    if not group:
        return False

    if not group.get("has_password"):
        return True

    room_id = group.get("room_id") or ""
    expected_hash = group.get("password_hash") or ""

    if not expected_hash:
        return False

    return make_group_password_hash(room_id, password) == expected_hash


async def get_group(room_id, include_deleted=False, include_password_hash=True):
    if not room_id:
        return None

    async with aiosqlite.connect(GROUPS_DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        if include_deleted:
            cursor = await db.execute(f"""
                SELECT {GROUP_SELECT_COLUMNS}
                FROM groups
                WHERE room_id = ?
            """, (room_id,))
        else:
            cursor = await db.execute(f"""
                SELECT {GROUP_SELECT_COLUMNS}
                FROM groups
                WHERE room_id = ?
                  AND is_deleted = 0
            """, (room_id,))

        row = await cursor.fetchone()
        await cursor.close()

        if not row:
            return None

        return group_row_to_dict(row, include_password_hash=include_password_hash)


async def get_all_groups(include_not_joined=True, include_password_hash=True):
    async with aiosqlite.connect(GROUPS_DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        if include_not_joined:
            cursor = await db.execute(f"""
                SELECT {GROUP_SELECT_COLUMNS}
                FROM groups
                WHERE is_deleted = 0
                ORDER BY created_at ASC
            """)
        else:
            cursor = await db.execute(f"""
                SELECT {GROUP_SELECT_COLUMNS}
                FROM groups
                WHERE is_joined = 1
                  AND is_deleted = 0
                ORDER BY created_at ASC
            """)

        rows = await cursor.fetchall()
        await cursor.close()

        return [
            group_row_to_dict(row, include_password_hash=include_password_hash)
            for row in rows
        ]


async def get_joined_groups(include_password_hash=True):
    return await get_all_groups(
        include_not_joined=False,
        include_password_hash=include_password_hash,
    )


async def check_group_password(room_id, password):
    group = await get_group(
        room_id,
        include_deleted=False,
        include_password_hash=True,
    )

    if not group:
        return False

    return check_group_password_value(group, password)

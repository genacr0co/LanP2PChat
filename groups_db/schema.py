import aiosqlite

from settings import GROUPS_DB_PATH

from .common import ensure_column, now_str


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
                is_joined INTEGER NOT NULL DEFAULT 0,
                has_password INTEGER NOT NULL DEFAULT 0,
                is_deleted INTEGER NOT NULL DEFAULT 0,
                deleted_at TEXT NOT NULL DEFAULT '',
                deleted_by TEXT NOT NULL DEFAULT ''
            )
        """)

        await ensure_column(
            db,
            "groups",
            "has_password",
            "has_password INTEGER NOT NULL DEFAULT 0",
        )

        await ensure_column(
            db,
            "groups",
            "is_deleted",
            "is_deleted INTEGER NOT NULL DEFAULT 0",
        )

        await ensure_column(
            db,
            "groups",
            "deleted_at",
            "deleted_at TEXT NOT NULL DEFAULT ''",
        )

        await ensure_column(
            db,
            "groups",
            "deleted_by",
            "deleted_by TEXT NOT NULL DEFAULT ''",
        )

        await db.execute("""
            CREATE TABLE IF NOT EXISTS group_messages (
                message_id TEXT PRIMARY KEY,
                room_id TEXT NOT NULL,
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
            "group_messages",
            "is_deleted",
            "is_deleted INTEGER NOT NULL DEFAULT 0",
        )

        await ensure_column(
            db,
            "group_messages",
            "deleted_at",
            "deleted_at TEXT NOT NULL DEFAULT ''",
        )

        await ensure_column(
            db,
            "group_messages",
            "deleted_by",
            "deleted_by TEXT NOT NULL DEFAULT ''",
        )

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_group_messages_room
            ON group_messages(room_id)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_group_messages_created_at
            ON group_messages(created_at)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_group_messages_is_deleted
            ON group_messages(is_deleted)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_groups_unique_name
            ON groups(unique_name)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_groups_is_deleted
            ON groups(is_deleted)
        """)

        await db.execute("""
            INSERT OR IGNORE INTO groups
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
        """, (
            "general",
            "Общий чат",
            "general",
            "",
            "system",
            now_str(),
            1,
            1,
            0,
            0,
            "",
            "",
        ))

        await db.execute("""
            UPDATE groups
            SET is_deleted = 0,
                deleted_at = '',
                deleted_by = '',
                is_joined = 1,
                is_creator = 1,
                password_hash = '',
                has_password = 0
            WHERE room_id = 'general'
        """)

        await db.execute("""
            UPDATE groups
            SET password_hash = '',
                has_password = 0
        """)

        await db.commit()
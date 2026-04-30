import aiosqlite

from settings import DIRECT_DB_PATH

from .common import ensure_column


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
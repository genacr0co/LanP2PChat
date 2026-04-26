import uuid
from datetime import datetime

import aiosqlite

from settings import DIRECT_DB_PATH


async def init_direct_db():
    async with aiosqlite.connect(DIRECT_DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS direct_chats (
                chat_id TEXT PRIMARY KEY,
                peer_id TEXT NOT NULL,
                peer_name TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS direct_messages (
                message_id TEXT PRIMARY KEY,
                chat_id TEXT NOT NULL,
                sender_id TEXT NOT NULL,
                username TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_direct_messages_chat
            ON direct_messages(chat_id)
        """)

        await db.commit()


def make_direct_chat_id(my_node_id, peer_node_id):
    ids = sorted([my_node_id, peer_node_id])
    return "direct_" + "_".join(ids)


async def save_direct_chat(chat):
    async with aiosqlite.connect(DIRECT_DB_PATH) as db:
        cursor = await db.execute("""
            INSERT OR IGNORE INTO direct_chats
            (chat_id, peer_id, peer_name, created_at)
            VALUES (?, ?, ?, ?)
        """, (
            chat["chat_id"],
            chat["peer_id"],
            chat["peer_name"],
            chat.get("created_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ))

        changed = cursor.rowcount > 0

        await cursor.close()
        await db.commit()

        return changed


async def get_direct_chat(chat_id):
    async with aiosqlite.connect(DIRECT_DB_PATH) as db:
        cursor = await db.execute("""
            SELECT chat_id, peer_id, peer_name, created_at
            FROM direct_chats
            WHERE chat_id = ?
        """, (chat_id,))

        row = await cursor.fetchone()
        await cursor.close()

        if not row:
            return None

        return {
            "chat_id": row[0],
            "peer_id": row[1],
            "peer_name": row[2],
            "created_at": row[3],
        }


async def get_direct_chats():
    async with aiosqlite.connect(DIRECT_DB_PATH) as db:
        cursor = await db.execute("""
            SELECT dc.chat_id, dc.peer_id, dc.peer_name, dc.created_at,
                   MAX(dm.created_at) AS last_message_time
            FROM direct_chats dc
            LEFT JOIN direct_messages dm ON dc.chat_id = dm.chat_id
            GROUP BY dc.chat_id
            ORDER BY last_message_time DESC, dc.created_at DESC
        """)

        rows = await cursor.fetchall()
        await cursor.close()

        return [
            {
                "chat_id": r[0],
                "peer_id": r[1],
                "peer_name": r[2],
                "created_at": r[3],
            }
            for r in rows
        ]


async def save_direct_message(msg):
    async with aiosqlite.connect(DIRECT_DB_PATH) as db:
        cursor = await db.execute("""
            INSERT OR IGNORE INTO direct_messages
            (message_id, chat_id, sender_id, username, message, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            msg.get("message_id") or str(uuid.uuid4()),
            msg["chat_id"],
            msg["sender_id"],
            msg["username"],
            msg["message"],
            msg.get("created_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ))

        changed = cursor.rowcount > 0

        await cursor.close()
        await db.commit()

        return changed


async def get_direct_messages(chat_id=None):
    async with aiosqlite.connect(DIRECT_DB_PATH) as db:
        if chat_id:
            cursor = await db.execute("""
                SELECT message_id, chat_id, sender_id, username, message, created_at
                FROM direct_messages
                WHERE chat_id = ?
                ORDER BY created_at ASC
            """, (chat_id,))
        else:
            cursor = await db.execute("""
                SELECT message_id, chat_id, sender_id, username, message, created_at
                FROM direct_messages
                ORDER BY created_at ASC
            """)

        rows = await cursor.fetchall()
        await cursor.close()

        return [
            {
                "message_id": r[0],
                "chat_id": r[1],
                "sender_id": r[2],
                "username": r[3],
                "message": r[4],
                "created_at": r[5],
            }
            for r in rows
        ]
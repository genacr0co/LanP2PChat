import sqlite3
import uuid
from datetime import datetime

from settings import DIRECT_DB_PATH


def direct_connect():
    return sqlite3.connect(DIRECT_DB_PATH)


def init_direct_db():
    con = direct_connect()
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS direct_chats (
            chat_id TEXT PRIMARY KEY,
            peer_id TEXT NOT NULL,
            peer_name TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS direct_messages (
            message_id TEXT PRIMARY KEY,
            chat_id TEXT NOT NULL,
            sender_id TEXT NOT NULL,
            username TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_direct_messages_chat
        ON direct_messages(chat_id)
    """)

    con.commit()
    con.close()


def make_direct_chat_id(my_node_id, peer_node_id):
    ids = sorted([my_node_id, peer_node_id])
    return "direct_" + "_".join(ids)


def save_direct_chat(chat):
    con = direct_connect()
    cur = con.cursor()

    cur.execute("""
        INSERT OR IGNORE INTO direct_chats
        (chat_id, peer_id, peer_name, created_at)
        VALUES (?, ?, ?, ?)
    """, (
        chat["chat_id"],
        chat["peer_id"],
        chat["peer_name"],
        chat.get("created_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ))

    changed = cur.rowcount > 0
    con.commit()
    con.close()

    return changed


def get_direct_chat(chat_id):
    con = direct_connect()
    cur = con.cursor()

    cur.execute("""
        SELECT chat_id, peer_id, peer_name, created_at
        FROM direct_chats
        WHERE chat_id = ?
    """, (chat_id,))

    row = cur.fetchone()
    con.close()

    if not row:
        return None

    return {
        "chat_id": row[0],
        "peer_id": row[1],
        "peer_name": row[2],
        "created_at": row[3],
    }


def get_direct_chats():
    con = direct_connect()
    cur = con.cursor()

    cur.execute("""
        SELECT dc.chat_id, dc.peer_id, dc.peer_name, dc.created_at,
               MAX(dm.created_at) AS last_message_time
        FROM direct_chats dc
        LEFT JOIN direct_messages dm ON dc.chat_id = dm.chat_id
        GROUP BY dc.chat_id
        ORDER BY last_message_time DESC, dc.created_at DESC
    """)

    rows = cur.fetchall()
    con.close()

    return [
        {
            "chat_id": r[0],
            "peer_id": r[1],
            "peer_name": r[2],
            "created_at": r[3],
        }
        for r in rows
    ]


def save_direct_message(msg):
    con = direct_connect()
    cur = con.cursor()

    cur.execute("""
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

    changed = cur.rowcount > 0
    con.commit()
    con.close()

    return changed


def get_direct_messages(chat_id=None):
    con = direct_connect()
    cur = con.cursor()

    if chat_id:
        cur.execute("""
            SELECT message_id, chat_id, sender_id, username, message, created_at
            FROM direct_messages
            WHERE chat_id = ?
            ORDER BY created_at ASC
        """, (chat_id,))
    else:
        cur.execute("""
            SELECT message_id, chat_id, sender_id, username, message, created_at
            FROM direct_messages
            ORDER BY created_at ASC
        """)

    rows = cur.fetchall()
    con.close()

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
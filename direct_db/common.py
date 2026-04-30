from datetime import datetime


DIRECT_MESSAGE_DELETE_MASK = "▒▒▒▒▒▒▒▒▒▒▒▒"


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


async def ensure_column(db, table_name, column_name, column_sql):
    cursor = await db.execute(f"PRAGMA table_info({table_name})")
    columns = await cursor.fetchall()
    await cursor.close()

    existing_columns = {col[1] for col in columns}

    if column_name not in existing_columns:
        await db.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}")


def direct_chat_row_to_dict(row):
    return {
        "chat_id": row["chat_id"],
        "peer_id": row["peer_id"],
        "peer_name": row["peer_name"],
        "created_at": row["created_at"],
        "is_deleted": bool(row["is_deleted"]),
        "deleted_at": row["deleted_at"] or "",
        "deleted_by": row["deleted_by"] or "",
    }


def direct_message_row_to_dict(row, mask_deleted=True):
    is_deleted = bool(row["is_deleted"])
    message = row["message"]

    if is_deleted and mask_deleted:
        message = DIRECT_MESSAGE_DELETE_MASK

    return {
        "message_id": row["message_id"],
        "chat_id": row["chat_id"],
        "sender_id": row["sender_id"],
        "username": row["username"],
        "message": message,
        "created_at": row["created_at"],
        "is_deleted": is_deleted,
        "deleted_at": row["deleted_at"] or "",
        "deleted_by": row["deleted_by"] or "",
    }
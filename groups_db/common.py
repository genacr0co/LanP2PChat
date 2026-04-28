from datetime import datetime


MESSAGE_DELETE_MASK = "▒▒▒▒▒▒▒▒▒▒▒▒"


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


async def ensure_column(db, table_name, column_name, column_sql):
    cursor = await db.execute(f"PRAGMA table_info({table_name})")
    columns = await cursor.fetchall()
    await cursor.close()

    existing_columns = {col[1] for col in columns}

    if column_name not in existing_columns:
        await db.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}")


def group_row_to_dict(row, include_password_hash=True):
    data = {
        "room_id": row["room_id"],
        "name": row["name"],
        "unique_name": row["unique_name"],
        "created_by": row["created_by"],
        "created_at": row["created_at"],
        "is_creator": bool(row["is_creator"]),
        "is_joined": bool(row["is_joined"]),
        "has_password": False,
        "is_deleted": bool(row["is_deleted"]),
        "deleted_at": row["deleted_at"] or "",
        "deleted_by": row["deleted_by"] or "",
    }

    if include_password_hash:
        data["password_hash"] = ""

    return data


def group_message_row_to_dict(row, mask_deleted=True):
    is_deleted = bool(row["is_deleted"])

    message = row["message"]

    if is_deleted and mask_deleted:
        message = MESSAGE_DELETE_MASK

    return {
        "message_id": row["message_id"],
        "room_id": row["room_id"],
        "sender_id": row["sender_id"],
        "username": row["username"],
        "message": message,
        "created_at": row["created_at"],
        "is_deleted": is_deleted,
        "deleted_at": row["deleted_at"] or "",
        "deleted_by": row["deleted_by"] or "",
    }
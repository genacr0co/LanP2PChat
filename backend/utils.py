import socket
import ipaddress
import psutil
import os
import sys  # Добавьте этот импорт

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()

    return ip


def get_broadcast_addresses():
    broadcasts = {"255.255.255.255"}

    for _, addresses in psutil.net_if_addrs().items():
        for addr in addresses:
            if addr.family != socket.AF_INET:
                continue

            ip = addr.address
            netmask = addr.netmask

            if not ip or not netmask or ip.startswith("127."):
                continue

            try:
                network = ipaddress.IPv4Network(f"{ip}/{netmask}", strict=False)
                broadcasts.add(str(network.broadcast_address))
            except Exception:
                pass

    return sorted(broadcasts)


# =========================
# VALIDATION
# =========================

def validate_message(data):
    required = [
        "message_id",
        "room_id",
        "sender_id",
        "username",
        "message",
        "created_at",
    ]

    if not isinstance(data, dict):
        return False

    if not all(k in data for k in required):
        return False

    if not str(data.get("message_id", "")).strip():
        return False

    if not str(data.get("room_id", "")).strip():
        return False

    if not str(data.get("sender_id", "")).strip():
        return False

    if not str(data.get("message", "")).strip():
        return False

    return True


def validate_room(data):
    required = [
        "room_id",
        "name",
        "created_by",
        "created_at",
    ]

    if not isinstance(data, dict):
        return False

    if not all(k in data for k in required):
        return False

    if not str(data.get("room_id", "")).strip():
        return False

    if not str(data.get("name", "")).strip():
        return False

    if not str(data.get("created_by", "")).strip():
        return False

    # Нормализуем
    data.setdefault("password_hash", "")
    data.setdefault("room_type", "group")

    return True


# =========================
# DIRECT VALIDATION
# =========================

def validate_direct_message(data):
    required = [
        "message_id",
        "chat_id",
        "sender_id",
        "username",
        "message",
        "created_at",
    ]

    if not isinstance(data, dict):
        return False

    if not all(k in data for k in required):
        return False

    if not str(data.get("message_id", "")).strip():
        return False

    if not str(data.get("chat_id", "")).strip():
        return False

    if not str(data.get("sender_id", "")).strip():
        return False

    if not str(data.get("message", "")).strip():
        return False

    return True


def validate_direct_chat(data):
    required = [
        "chat_id",
        "peer_id",
        "peer_name",
        "created_at",
    ]

    if not isinstance(data, dict):
        return False

    if not all(k in data for k in required):
        return False

    if not str(data.get("chat_id", "")).strip():
        return False

    if not str(data.get("peer_id", "")).strip():
        return False

    if not str(data.get("peer_name", "")).strip():
        return False

    return True

# =========================
# NEW SETTINGS FOR ANDROID
# =========================

# Для Android, возможно, вам нужно будет работать с файлом в нестандартной папке
def get_app_data_path():
    if getattr(sys, "frozen", False):  # Проверка на Android
        return os.path.join(sys._MEIPASS, "data")
    
    # Если не на Android, берем стандартное место
    return os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "LANP2PChat")

# Получение пути к локальным данным (для хранения бд и данных)
LOCAL_DATA_DIR = get_app_data_path()
os.makedirs(LOCAL_DATA_DIR, exist_ok=True)
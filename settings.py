import os
import sys

APP_NAME = "LAN P2P Chat"

HTTP_PORT = 8765
DISCOVERY_PORT = 9999

DISCOVERY_INTERVAL = 2
SYNC_INTERVAL = 5
PEER_TIMEOUT = 20


def app_dir():
    if getattr(sys, "frozen", False):
        # Для Android
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def resource_path(relative_path):
    if getattr(sys, "frozen", False):
        # Для Android: использует ресурсы из sys._MEIPASS (пакетирование с PyInstaller)
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(app_dir(), relative_path)


# базовая папка
BASE_DIR = app_dir()

# static - путь к static папке
ANDROID_STATIC_DIR = os.environ.get("LANP2PCHAT_STATIC_DIR")

if ANDROID_STATIC_DIR:
    STATIC_DIR = ANDROID_STATIC_DIR  # для Android используем путь, переданный из android_server.py
else:
    STATIC_DIR = resource_path("static")

# локальные данные пользователя
ANDROID_DATA_DIR = os.environ.get("LANP2PCHAT_DATA_DIR")

if ANDROID_DATA_DIR:
    LOCAL_DATA_DIR = os.path.join(ANDROID_DATA_DIR, "LANP2PChat")
else:
    LOCAL_DATA_DIR = os.path.join(
        os.environ.get("LOCALAPPDATA", BASE_DIR),
        "LANP2PChat"
    )

os.makedirs(LOCAL_DATA_DIR, exist_ok=True)

# ====== НОВЫЕ БД ======

# пользователь (настройки, username, node_id)
USER_DB_PATH = os.path.join(LOCAL_DATA_DIR, "user.db")

# группы
GROUPS_DB_PATH = os.path.join(LOCAL_DATA_DIR, "groups.db")

# личные сообщения
DIRECT_DB_PATH = os.path.join(LOCAL_DATA_DIR, "direct.db")
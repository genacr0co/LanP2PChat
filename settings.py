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
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def resource_path(relative_path):
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(app_dir(), relative_path)


# базовая папка
BASE_DIR = app_dir()

# static
STATIC_DIR = resource_path("static")

# локальные данные пользователя
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
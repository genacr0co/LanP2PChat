import os
import sys

APP_NAME = "LAN P2P Chat"

HTTP_PORT = 8765
DISCOVERY_PORT = 9999

# Каждое устройство раз в 5 секунд отправляет broadcast heartbeat.
DISCOVERY_INTERVAL = 5

SYNC_INTERVAL = 5

# Если от конкретного peer-а нет сигнала 15 секунд,
# считаем, что он отключился, и удаляем только его.
#
# Логика:
# 5 секунд — обычный интервал сигнала.
# +10 секунд — запас на лаги/пропущенный пакет.
PEER_TIMEOUT = 15


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
    STATIC_DIR = ANDROID_STATIC_DIR
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

# ====== БД ======

USER_DB_PATH = os.path.join(LOCAL_DATA_DIR, "user.db")
GROUPS_DB_PATH = os.path.join(LOCAL_DATA_DIR, "groups.db")
DIRECT_DB_PATH = os.path.join(LOCAL_DATA_DIR, "direct.db")
# ====== P2P / GLOBAL DISCOVERY ======

# Начальные ноды для входа в распределённую сеть.
# Форматы:
#   "192.168.1.100:8765"
#   "node.example.com:8765"
#   {"host": "node.example.com", "port": 8765}
BOOTSTRAP_NODES = [
        "10.86.1.75:8765",
    "10.86.90.65:8765",
]

# Дополнительные подсети для будущих явных LAN-сценариев.
# Auto-scan уже умеет строить диапазоны от интерфейсов сам, поэтому обычно
# это поле можно оставить пустым.
EXTRA_SUBNETS = [
        "10.86.0.0/23",
    "10.86.90.0/24",
]

# Peer Exchange: обмен списком известных peer-ов через уже установленные
# WebSocket-соединения.
PEX_INTERVAL = 30
PEX_MAX_PEERS = 100
PEX_CONNECT_LIMIT = 60

# Основа под будущую ручную/управляемую смену порта.
# Полная автоматическая смена порта требует отдельного механизма перезапуска
# backend-сервера, поэтому сейчас по умолчанию выключено.
ENABLE_PORT_HOPPING = False
PORT_HOPPING_INTERVAL = 300
PORT_HOPPING_MIN_PORT = 8000
PORT_HOPPING_MAX_PORT = 9000

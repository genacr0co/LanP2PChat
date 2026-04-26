import threading


# =========================
# CURRENT NODE STATE
# =========================

# ID текущего узла.
# Заполняется в server.py после init_user_db().
NODE_ID = None


# =========================
# NETWORK STATE
# =========================

# Найденные peer'ы:
# node_id -> {
#   "node_id": "...",
#   "username": "...",
#   "ip": "...",
#   "port": 8000,
#   "last_seen": 1234567890
# }
peers = {}

# Активные async WebSocket соединения:
# node_id -> websocket
peer_connections = {}

# Очереди отправки:
# node_id -> asyncio.Queue
peer_queues = {}

# Async задачи:
# node_id -> asyncio.Task
peer_tasks = {}

# Loop, в котором живёт async P2P layer
network_loop = None

# Lock для peer state.
# Пока оставляем threading.Lock, потому что state используется из разных потоков:
# uvicorn thread + background async thread.
peer_lock = threading.Lock()


# =========================
# UI STATE
# =========================

# Локальные браузерные WebSocket-клиенты
local_web_clients = set()

# Lock для local_web_clients
web_clients_lock = threading.Lock()

# Loop, где живёт UI websocket
ui_loop = None


# =========================
# TEMP REQUEST STATE
# =========================

# Временные ответы на запросы:
# search_id/request_id -> data/list
pending_requests = {}

pending_requests_lock = threading.Lock()


# =========================
# OUTGOING PENDING STATE
# =========================

# Позже сюда можно складывать сообщения,
# которые не удалось отправить peer'у.
#
# Пример:
# message_id -> {
#   "target_id": "...",
#   "packet": {...},
#   "attempts": 0,
#   "created_at": "...",
# }
pending_outgoing = {}

pending_outgoing_lock = threading.Lock()
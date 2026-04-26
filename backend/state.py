import threading


# текущий узел
NODE_ID = None


# =========================
# NETWORK STATE
# =========================

# найденные peer'ы:
# node_id -> {
#   node_id,
#   username,
#   ip,
#   port,
#   last_seen
# }
peers = {}

# активные async WebSocket соединения:
# node_id -> websocket
peer_connections = {}

# очереди отправки:
# node_id -> asyncio.Queue
peer_queues = {}

# async задачи:
# node_id -> asyncio.Task
peer_tasks = {}

# loop, в котором живёт async P2P layer
network_loop = None

# lock для peer state
peer_lock = threading.Lock()


# =========================
# UI STATE
# =========================

local_web_clients = set()
web_clients_lock = threading.Lock()
ui_loop = None


# =========================
# TEMP REQUEST STATE
# =========================

pending_requests = {}
pending_requests_lock = threading.Lock()
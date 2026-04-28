"""
Compatibility layer.

Раньше вся P2P-логика лежала в этом файле.
Теперь код разделён по backend/p2p/*, но старые импорты оставлены рабочими.

Например, старый код всё ещё может делать:

from .p2p_async import broadcast_packet_async
from .p2p_async import _add_or_update_peer, _touch_peer
"""

from .p2p.api import (
    start_network_layer,
    send_packet_to_peer_async,
    broadcast_packet_async,
    send_packet_to_peer,
    broadcast_packet,
    broadcast_ws_packet,
    _send_packet_to_peer_in_network_loop,
    _broadcast_packet_in_network_loop,
)

from .p2p.discovery import (
    discovery_announce_loop,
    discovery_broadcast_loop,
    discovery_listen_loop,
)

from .p2p.connection import (
    peer_manager_loop,
    ensure_peer_task,
    peer_connection_task,
    peer_sender_loop,
    peer_receiver_loop,
    send_peer_hello as _send_peer_hello,
)

from .p2p.peers import (
    DISCOVERY_PACKET_TYPE,
    PEER_HELLO_PACKET_TYPE,
    safe_int as _safe_int,
    get_platform_name as _get_platform_name,
    build_discovery_packet as _build_discovery_packet,
    build_peer_hello_packet as _build_peer_hello_packet,
    add_or_update_peer as _add_or_update_peer,
    touch_peer as _touch_peer,
)
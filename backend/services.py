import json

from . import state


async def send_to_local_web_clients(packet):
    dead = []
    text = json.dumps(packet, ensure_ascii=False)

    with state.web_clients_lock:
        clients = list(state.local_web_clients)

    for client in clients:
        try:
            await client.send_text(text)
        except Exception:
            dead.append(client)

    if dead:
        with state.web_clients_lock:
            for client in dead:
                state.local_web_clients.discard(client)


async def notify_ui(packet):
    try:
        await send_to_local_web_clients(packet)
    except Exception:
        pass


async def handle_packet(packet):
    if not isinstance(packet, dict):
        return False

    packet_type = packet.get("type")
    data = packet.get("data")

    if packet_type in ("group", "room"):
        from .group_service import receive_group
        return await receive_group(data, forward=False)

    if packet_type in ("group_message", "message"):
        from .group_service import receive_group_message
        return await receive_group_message(data, forward=False)

    if packet_type == "direct_message":
        from .direct_service import receive_direct_packet
        return await receive_direct_packet(data)

    if packet_type == "group_search_request":
        from .search_service import receive_group_search_request
        return await receive_group_search_request(data)

    if packet_type == "group_search_response":
        from .search_service import receive_group_search_response
        return await receive_group_search_response(data)

    if packet_type == "group_join_check":
        from .search_service import receive_group_join_check
        return await receive_group_join_check(data)

    if packet_type == "group_join_result":
        from .search_service import receive_group_join_result
        return await receive_group_join_result(data)

    return False


async def receive_typing(data, forward=True):
    return False
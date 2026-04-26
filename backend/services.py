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
    except Exception as e:
        print("[UI NOTIFY ERROR]", e)


async def handle_packet(packet):
    if not isinstance(packet, dict):
        return False

    packet_type = packet.get("type")
    data = packet.get("data")

    try:
        if packet_type in ("group", "room"):
            from .group_service import receive_group
            return await receive_group(data, forward=False)

        if packet_type in ("group_message", "message"):
            from .group_service import receive_group_message
            return await receive_group_message(data, forward=False)

        if packet_type == "direct_message":
            from .direct_service import receive_direct_packet
            return await receive_direct_packet(data)

        # Поиск групп и typing пока отключены.
        # Игнорируем старые пакеты, если они прилетят от старой версии клиента.
        if packet_type in (
            "group_search_request",
            "group_search_response",
            "group_join_check",
            "group_join_result",
            "typing",
        ):
            return False

    except Exception as e:
        print("[HANDLE PACKET ERROR]", packet_type, e)
        return False

    return False
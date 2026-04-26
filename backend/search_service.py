from async_groups_database import (
    save_discovered_group,
    find_created_groups,
    check_group_password,
)

from . import state
from .services import notify_ui
from .p2p_async import send_packet_to_peer_async


async def receive_discovered_group(data):
    if not isinstance(data, dict):
        return False

    changed = await save_discovered_group(data)

    if not changed:
        return False

    await notify_ui({
        "type": "group_found",
        "data": data,
    })

    return True


async def receive_group_search_request(data):
    if not isinstance(data, dict):
        return False

    query = (data.get("query") or "").strip()
    requester_id = data.get("requester_id", "")
    search_id = data.get("search_id", "")

    if not query or not requester_id or not search_id:
        return False

    if requester_id == state.NODE_ID:
        return False

    results = await find_created_groups(query)

    if not results:
        return False

    sent_any = False

    for group in results:
        group = dict(group)
        group["search_id"] = search_id

        sent = await send_packet_to_peer_async(requester_id, {
            "type": "group_search_response",
            "data": group,
        })

        if sent:
            sent_any = True

    return sent_any


async def receive_group_search_response(data):
    if not isinstance(data, dict):
        return False

    search_id = data.get("search_id")

    if search_id:
        with state.pending_requests_lock:
            state.pending_requests.setdefault(search_id, [])
            state.pending_requests[search_id].append(data)

    return await receive_discovered_group(data)


async def receive_group_join_check(data):
    if not isinstance(data, dict):
        return False

    requester_id = data.get("requester_id", "")
    request_id = data.get("request_id", "")
    room_id = data.get("room_id", "")
    password = data.get("password", "")

    if not requester_id or not request_id or not room_id:
        return False

    if requester_id == state.NODE_ID:
        return False

    ok = await check_group_password(room_id, password)

    return await send_packet_to_peer_async(requester_id, {
        "type": "group_join_result",
        "data": {
            "request_id": request_id,
            "room_id": room_id,
            "ok": ok,
        },
    })


async def receive_group_join_result(data):
    if not isinstance(data, dict):
        return False

    request_id = data.get("request_id")

    if not request_id:
        return False

    with state.pending_requests_lock:
        state.pending_requests[request_id] = data

    return True
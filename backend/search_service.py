from groups_database import (
    save_discovered_group,
    find_created_groups,
    check_group_password,
)

from . import state
from .services import notify_ui
from .p2p_async import send_packet_to_peer


def receive_discovered_group(data):
    if not isinstance(data, dict):
        return False

    changed = save_discovered_group(data)

    if changed:
        notify_ui({
            "type": "group_found",
            "data": data,
        })

    return changed


def receive_group_search_request(data):
    if not isinstance(data, dict):
        return False

    query = (data.get("query") or "").strip()
    requester_id = data.get("requester_id", "")
    search_id = data.get("search_id", "")

    if not query or not requester_id or not search_id:
        return False

    results = find_created_groups(query)

    if not results:
        return False

    for group in results:
        group["search_id"] = search_id

        send_packet_to_peer(requester_id, {
            "type": "group_search_response",
            "data": group,
        })

    return True


def receive_group_search_response(data):
    if not isinstance(data, dict):
        return False

    search_id = data.get("search_id")

    if search_id:
        with state.pending_requests_lock:
            state.pending_requests.setdefault(search_id, [])
            state.pending_requests[search_id].append(data)

    return receive_discovered_group(data)


def receive_group_join_check(data):
    if not isinstance(data, dict):
        return False

    requester_id = data.get("requester_id", "")
    request_id = data.get("request_id", "")
    room_id = data.get("room_id", "")
    password = data.get("password", "")

    if not requester_id or not request_id or not room_id:
        return False

    ok = check_group_password(room_id, password)

    send_packet_to_peer(requester_id, {
        "type": "group_join_result",
        "data": {
            "request_id": request_id,
            "room_id": room_id,
            "ok": ok,
        },
    })

    return True


def receive_group_join_result(data):
    if not isinstance(data, dict):
        return False

    request_id = data.get("request_id")

    if not request_id:
        return False

    with state.pending_requests_lock:
        state.pending_requests[request_id] = data

    return True
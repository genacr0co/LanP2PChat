import asyncio
import ipaddress
import json
import random
import socket
import time

from settings import HTTP_PORT, EXTRA_SUBNETS
from .. import state
from ..utils import get_local_ip

from .discovery import is_android_runtime
from .peers import add_or_update_peer

try:
    import psutil
except Exception:
    psutil = None


# =========================
# AUTO-SCAN CONFIG
# =========================

AUTO_SCAN_ENABLED_ON_ANDROID = False
AUTO_SCAN_CONNECT_TIMEOUT = 0.35
AUTO_SCAN_READ_TIMEOUT = 0.7
AUTO_SCAN_CONCURRENCY = 192
AUTO_SCAN_INITIAL_LIMIT = 4096
AUTO_SCAN_BATCH_SIZE = 768
AUTO_SCAN_IDLE_SLEEP = 8
AUTO_SCAN_ROUND_SLEEP = 60
AUTO_SCAN_PORT = HTTP_PORT


# =========================
# IP HELPERS
# =========================

def _is_valid_scan_ip(ip):
    if not ip:
        return False

    try:
        parsed = ipaddress.IPv4Address(ip)
    except Exception:
        return False

    if parsed.is_loopback:
        return False

    if parsed.is_multicast:
        return False

    if parsed.is_unspecified:
        return False

    if parsed.is_link_local:
        return False

    return True


def _is_private_lan_ip(ip):
    try:
        parsed = ipaddress.IPv4Address(ip)
        return parsed.is_private
    except Exception:
        return False


def _safe_network_from_ip_mask(ip, netmask):
    try:
        return ipaddress.IPv4Network(f"{ip}/{netmask}", strict=False)
    except Exception:
        return None



def _get_extra_config_networks():
    networks = []

    for item in EXTRA_SUBNETS:
        try:
            network = ipaddress.IPv4Network(str(item).strip(), strict=False)
        except Exception:
            continue

        if network.version != 4:
            continue

        networks.append((str(network.network_address), network))

    return networks

def _get_local_interface_networks():
    """
    Возвращает IPv4-сети всех нормальных LAN-интерфейсов.

    Важно:
    - не привязываемся к конкретным адресам типа 10.86.x.x;
    - используем реальные IP/маски текущего устройства;
    - если psutil недоступен, fallback — текущий get_local_ip() как /24.
    """
    networks = []

    if psutil is not None:
        try:
            for _, addresses in psutil.net_if_addrs().items():
                for addr in addresses:
                    if addr.family != socket.AF_INET:
                        continue

                    ip = addr.address
                    netmask = addr.netmask

                    if not _is_valid_scan_ip(ip) or not netmask:
                        continue

                    network = _safe_network_from_ip_mask(ip, netmask)
                    if network:
                        networks.append((ip, network))
        except Exception as e:
            print("[AUTO SCAN INTERFACES WARNING]", e)

    if not networks:
        ip = get_local_ip()
        if _is_valid_scan_ip(ip):
            network = _safe_network_from_ip_mask(ip, "255.255.255.0")
            if network:
                networks.append((ip, network))

    # Убираем дубли, сохраняя порядок.
    seen = set()
    result = []

    for ip, network in networks:
        key = str(network)
        if key in seen:
            continue
        seen.add(key)
        result.append((ip, network))

    return result


def _iter_hosts_limited(network, max_hosts=4096):
    """
    Аккуратно отдаёт hosts() для сети.
    Огромные сети целиком тут не раскрываем.
    """
    count = 0

    try:
        for host in network.hosts():
            yield str(host)
            count += 1
            if count >= max_hosts:
                break
    except Exception:
        return


def _build_same_private_area_prefixes(local_ip):
    """
    Строит динамические /24-префиксы вокруг текущего приватного адреса.

    Это не хардкод под 10.86:
    - для 10.A.B.C сканируем 10.A.0.0/16 волнами по /24;
    - для 172.16-31.B.C сканируем 172.X.0.0/16;
    - для 192.168.B.C сканируем 192.168.0.0/16.

    Так LanP2PChat может находить routed-подсети внутри одной организации,
    если HTTP/WebSocket между ними разрешён, а UDP discovery не маршрутизируется.
    """
    try:
        parts = [int(x) for x in local_ip.split(".")]
        if len(parts) != 4:
            return []
    except Exception:
        return []

    a, b, c, _ = parts

    prefixes = []

    if a == 10:
        base_a = 10
        base_b = b
    elif a == 172 and 16 <= b <= 31:
        base_a = 172
        base_b = b
    elif a == 192 and b == 168:
        base_a = 192
        base_b = 168
    else:
        return []

    # Приоритет:
    # 1. своя /24;
    # 2. низкие подсети 0,1,2... — часто там сидят шлюзы/проводные VLAN;
    # 3. соседние подсети вокруг своей;
    # 4. остальные /24.
    ordered_third_octets = []

    def add_octet(value):
        if 0 <= value <= 255 and value not in ordered_third_octets:
            ordered_third_octets.append(value)

    add_octet(c)

    for value in range(0, 16):
        add_octet(value)

    for delta in range(1, 17):
        add_octet(c - delta)
        add_octet(c + delta)

    for value in range(0, 256):
        add_octet(value)

    for third in ordered_third_octets:
        prefixes.append(f"{base_a}.{base_b}.{third}")

    return prefixes


def build_auto_scan_targets():
    """
    Формирует список IP для auto-scan без привязки к конкретной сети.

    Что попадает в список:
    - адреса из реальных локальных сетей интерфейсов;
    - динамические /24 внутри той же приватной области /16;
    - уже известные peer IP — первыми, чтобы быстро перепроверять старые адреса.
    """
    local_ips = set()
    targets = []
    seen = set()

    def add_ip(ip):
        if not _is_valid_scan_ip(ip):
            return
        if ip in local_ips:
            return
        if ip in seen:
            return
        seen.add(ip)
        targets.append(ip)

    with state.peer_lock:
        known_peer_ips = [
            peer.get("ip")
            for peer in state.peers.values()
            if isinstance(peer, dict)
        ]

    for ip in known_peer_ips:
        add_ip(ip)

    interface_networks = _get_local_interface_networks()
    extra_networks = _get_extra_config_networks()

    for local_ip, network in interface_networks:
        if _is_valid_scan_ip(local_ip):
            local_ips.add(local_ip)

    # Сначала реальные локальные сети интерфейсов.
    for _, network in interface_networks:
        max_hosts = 4096
        if network.num_addresses <= 4096:
            max_hosts = int(network.num_addresses)

        for ip in _iter_hosts_limited(network, max_hosts=max_hosts):
            add_ip(ip)

    # Потом явно заданные дополнительные подсети из settings.EXTRA_SUBNETS.
    for _, network in extra_networks:
        max_hosts = 4096
        if network.num_addresses <= 4096:
            max_hosts = int(network.num_addresses)

        for ip in _iter_hosts_limited(network, max_hosts=max_hosts):
            add_ip(ip)

    # Потом приватная область вокруг каждого локального IP.
    for local_ip, _ in interface_networks:
        if not _is_private_lan_ip(local_ip):
            continue

        prefixes = _build_same_private_area_prefixes(local_ip)

        for prefix in prefixes:
            for last in range(1, 255):
                add_ip(f"{prefix}.{last}")

    return targets


# =========================
# HTTP PROBE
# =========================

async def _http_get_json(ip, port=AUTO_SCAN_PORT):
    reader = None
    writer = None

    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, port),
            timeout=AUTO_SCAN_CONNECT_TIMEOUT,
        )

        request = (
            "GET /api/me HTTP/1.1\r\n"
            f"Host: {ip}:{port}\r\n"
            "User-Agent: LanP2PChat-AutoScan\r\n"
            "Connection: close\r\n"
            "Accept: application/json\r\n"
            "\r\n"
        )

        writer.write(request.encode("utf-8"))
        await writer.drain()

        raw = await asyncio.wait_for(
            reader.read(65536),
            timeout=AUTO_SCAN_READ_TIMEOUT,
        )

        if not raw:
            return None

        text = raw.decode("utf-8", errors="ignore")

        if "\r\n\r\n" not in text:
            return None

        headers, body = text.split("\r\n\r\n", 1)

        if "200" not in headers.split("\r\n", 1)[0]:
            return None

        return json.loads(body)

    except Exception:
        return None

    finally:
        if writer is not None:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass


def _extract_username_from_api_me(payload):
    if not isinstance(payload, dict):
        return "Аноним"

    node_id = payload.get("node_id")
    users = payload.get("users")

    if isinstance(users, list):
        for user in users:
            if not isinstance(user, dict):
                continue
            if user.get("node_id") == node_id:
                return user.get("username") or "Аноним"

    return payload.get("username") or "Аноним"


def _learn_peer_from_api_me(payload, fallback_ip, source="http_scan"):
    if not isinstance(payload, dict):
        return False

    node_id = payload.get("node_id")

    if not node_id or node_id == state.NODE_ID:
        return False

    peer_ip = payload.get("ip") or fallback_ip
    peer_port = payload.get("port") or HTTP_PORT

    packet = {
        "node_id": node_id,
        "username": _extract_username_from_api_me(payload),
        "ip": peer_ip,
        "port": peer_port,
        "platform": payload.get("platform", "unknown"),
    }

    return add_or_update_peer(packet, fallback_ip or peer_ip, source=source)


def _learn_gossip_users_from_api_me(payload):
    """
    Используем /api/me как простой peer gossip:
    если найденный клиент уже знает других peer-ов, берём их IP тоже.
    """
    if not isinstance(payload, dict):
        return 0

    users = payload.get("users")
    if not isinstance(users, list):
        return 0

    added = 0

    for user in users:
        if not isinstance(user, dict):
            continue

        node_id = user.get("node_id")
        ip = user.get("ip")

        if not node_id or node_id == state.NODE_ID:
            continue

        if not _is_valid_scan_ip(ip):
            continue

        packet = {
            "node_id": node_id,
            "username": user.get("username", "Аноним"),
            "ip": ip,
            "port": user.get("port") or HTTP_PORT,
            "platform": user.get("platform", "unknown"),
        }

        if add_or_update_peer(packet, ip, source="peer_gossip"):
            added += 1

    return added


async def _probe_ip(ip, semaphore):
    async with semaphore:
        payload = await _http_get_json(ip, AUTO_SCAN_PORT)

    if not payload:
        return False

    learned_self = _learn_peer_from_api_me(payload, ip, source="http_scan")
    learned_gossip = _learn_gossip_users_from_api_me(payload)

    if learned_self or learned_gossip:
        node_id = payload.get("node_id", "unknown")
        print(
            f"[AUTO SCAN FOUND] ip={ip} "
            f"node_id={node_id} gossip={learned_gossip}"
        )
        return True

    return False


async def _scan_targets(targets, limit=None):
    if not targets:
        return 0

    if limit is not None:
        targets = targets[:limit]

    semaphore = asyncio.Semaphore(AUTO_SCAN_CONCURRENCY)
    found = 0

    for start in range(0, len(targets), AUTO_SCAN_CONCURRENCY):
        chunk = targets[start:start + AUTO_SCAN_CONCURRENCY]
        results = await asyncio.gather(
            *[_probe_ip(ip, semaphore) for ip in chunk],
            return_exceptions=True,
        )

        for result in results:
            if result is True:
                found += 1

        await asyncio.sleep(0)

    return found


# =========================
# AUTO-SCAN LOOP
# =========================

async def auto_scan_loop():
    """
    HTTP fallback discovery.

    Зачем нужен:
    - multicast/broadcast часто не проходят между routed-подсетями;
    - если прямой GET /api/me работает, этот scan найдёт peer-а;
    - работает только на ПК, Android не трогаем.

    Не хардкодим сеть:
    - строим диапазоны от текущих интерфейсов и их приватной области;
    - сканируем волнами, с таймаутами и ограничением параллельности.
    """
    if is_android_runtime() and not AUTO_SCAN_ENABLED_ON_ANDROID:
        print("[AUTO SCAN] disabled on Android")
        return

    await asyncio.sleep(AUTO_SCAN_IDLE_SLEEP)

    cursor = 0

    while True:
        try:
            targets = build_auto_scan_targets()

            if not targets:
                await asyncio.sleep(AUTO_SCAN_ROUND_SLEEP)
                continue

            # Первый проход после старта — более быстрый: свои сети + первые /24
            # приватной области. Для примера 10.86.90.x это быстро захватит
            # 10.86.90.x, затем 10.86.0.x, 10.86.1.x и т.д.
            if cursor == 0:
                await _scan_targets(targets, limit=AUTO_SCAN_INITIAL_LIMIT)
                cursor = min(AUTO_SCAN_INITIAL_LIMIT, len(targets))

            batch = targets[cursor:cursor + AUTO_SCAN_BATCH_SIZE]

            if not batch:
                cursor = 0
                random.shuffle(targets)
                await asyncio.sleep(AUTO_SCAN_ROUND_SLEEP)
                continue

            await _scan_targets(batch)

            cursor += AUTO_SCAN_BATCH_SIZE

        except asyncio.CancelledError:
            break

        except Exception as e:
            print("[AUTO SCAN LOOP ERROR]", e)

        await asyncio.sleep(AUTO_SCAN_IDLE_SLEEP)

import socket
import ipaddress

try:
    import psutil
except Exception:
    psutil = None


# =========================
# NETWORK UTILS
# =========================

def _is_valid_lan_ipv4(ip):
    """
    Проверяет, что IP похож на нормальный LAN IPv4,
    а не loopback / мусор / IPv6 / auto-link address.
    """
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

    # 169.254.x.x — auto-link address.
    # Обычно это значит, что устройство не получило нормальный IP от роутера.
    if str(parsed).startswith("169.254."):
        return False

    return True


def _prefer_lan_ip(ips):
    """
    Выбирает лучший IP из списка.

    Приоритет:
    1. Частные LAN-адреса: 192.168.x.x / 10.x.x.x / 172.16-31.x.x
    2. Любой другой валидный IPv4
    3. 127.0.0.1 как самый последний fallback
    """
    valid_ips = []

    for ip in ips:
        if _is_valid_lan_ipv4(ip):
            valid_ips.append(ip)

    if not valid_ips:
        return "127.0.0.1"

    private_ips = []

    for ip in valid_ips:
        try:
            parsed = ipaddress.IPv4Address(ip)
            if parsed.is_private:
                private_ips.append(ip)
        except Exception:
            pass

    if private_ips:
        return sorted(private_ips)[0]

    return sorted(valid_ips)[0]


def _get_ips_from_psutil():
    ips = []

    if psutil is None:
        return ips

    try:
        for _, addresses in psutil.net_if_addrs().items():
            for addr in addresses:
                if addr.family != socket.AF_INET:
                    continue

                ip = addr.address

                if _is_valid_lan_ipv4(ip):
                    ips.append(ip)
    except Exception:
        pass

    return ips


def _get_ip_by_udp_route(target_host, target_port):
    """
    Получает локальный IP через UDP connect.

    UDP connect не отправляет пакет физически,
    но ОС выбирает интерфейс, через который пошёл бы маршрут.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        s.connect((target_host, target_port))
        ip = s.getsockname()[0]

        if _is_valid_lan_ipv4(ip):
            return ip

    except Exception:
        pass

    finally:
        s.close()

    return None


def _get_ips_from_hostname():
    ips = []

    try:
        hostname = socket.gethostname()
        addresses = socket.getaddrinfo(hostname, None, socket.AF_INET)

        for item in addresses:
            ip = item[4][0]

            if _is_valid_lan_ipv4(ip):
                ips.append(ip)

    except Exception:
        pass

    return ips


def get_local_ip():
    """
    Возвращает локальный LAN IP текущего устройства.

    Важно для LanP2PChat:
    - нельзя рекламировать 127.0.0.1 другим peer-ам;
    - Android может иметь psutil=None;
    - интернет может отсутствовать;
    - поэтому используем несколько способов.
    """
    candidates = []

    # 1. Самый точный способ на ПК, если psutil доступен.
    candidates.extend(_get_ips_from_psutil())

    # 2. Маршрут до multicast-группы.
    # Это ближе к нашей реальной discovery-сети, чем 8.8.8.8.
    multicast_ip = _get_ip_by_udp_route("239.255.42.99", 8765)
    if multicast_ip:
        candidates.append(multicast_ip)

    # 3. Старый fallback через внешний адрес.
    # UDP connect обычно не отправляет пакет, только выбирает интерфейс.
    internet_route_ip = _get_ip_by_udp_route("8.8.8.8", 80)
    if internet_route_ip:
        candidates.append(internet_route_ip)

    # 4. Hostname fallback.
    candidates.extend(_get_ips_from_hostname())

    return _prefer_lan_ip(candidates)


def get_broadcast_addresses():
    broadcasts = {"255.255.255.255"}

    # Android / Chaquopy fallback:
    # если psutil нет, просто используем общий broadcast.
    # Основной discovery теперь должен идти через multicast.
    if psutil is None:
        return sorted(broadcasts)

    for _, addresses in psutil.net_if_addrs().items():
        for addr in addresses:
            if addr.family != socket.AF_INET:
                continue

            ip = addr.address
            netmask = addr.netmask

            if not ip or not netmask or not _is_valid_lan_ipv4(ip):
                continue

            try:
                network = ipaddress.IPv4Network(f"{ip}/{netmask}", strict=False)
                broadcasts.add(str(network.broadcast_address))
            except Exception:
                pass

    return sorted(broadcasts)


# =========================
# VALIDATION
# =========================

def validate_message(data):
    required = [
        "message_id",
        "room_id",
        "sender_id",
        "username",
        "message",
        "created_at",
    ]

    if not isinstance(data, dict):
        return False

    if not all(k in data for k in required):
        return False

    if not str(data.get("message_id", "")).strip():
        return False

    if not str(data.get("room_id", "")).strip():
        return False

    if not str(data.get("sender_id", "")).strip():
        return False

    if not str(data.get("message", "")).strip():
        return False

    return True


def validate_room(data):
    required = [
        "room_id",
        "name",
        "created_by",
        "created_at",
    ]

    if not isinstance(data, dict):
        return False

    if not all(k in data for k in required):
        return False

    if not str(data.get("room_id", "")).strip():
        return False

    if not str(data.get("name", "")).strip():
        return False

    if not str(data.get("created_by", "")).strip():
        return False

    if not str(data.get("created_at", "")).strip():
        return False

    # Нормализуем старые/неполные P2P-пакеты
    data.setdefault("unique_name", "")
    data.setdefault("description", "")
    data.setdefault("password_hash", "")
    data.setdefault("room_type", "group")
    data.setdefault("is_creator", False)
    data.setdefault("is_joined", False)
    data.setdefault("has_password", False)

    # Нормализуем удаление группы
    data["is_deleted"] = bool(data.get("is_deleted", False))
    data["deleted_at"] = data.get("deleted_at") or ""
    data["deleted_by"] = data.get("deleted_by") or ""

    return True
# =========================
# DIRECT VALIDATION
# =========================

def validate_direct_message(data):
    required = [
        "message_id",
        "chat_id",
        "sender_id",
        "username",
        "message",
        "created_at",
    ]

    if not isinstance(data, dict):
        return False

    if not all(k in data for k in required):
        return False

    if not str(data.get("message_id", "")).strip():
        return False

    if not str(data.get("chat_id", "")).strip():
        return False

    if not str(data.get("sender_id", "")).strip():
        return False

    if not str(data.get("message", "")).strip():
        return False

    return True


def validate_direct_chat(data):
    required = [
        "chat_id",
        "peer_id",
        "peer_name",
        "created_at",
    ]

    if not isinstance(data, dict):
        return False

    if not all(k in data for k in required):
        return False

    if not str(data.get("chat_id", "")).strip():
        return False

    if not str(data.get("peer_id", "")).strip():
        return False

    if not str(data.get("peer_name", "")).strip():
        return False

    return True
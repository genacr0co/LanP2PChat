import json
import socket
import asyncio
import os
import platform

from user_db.profile import get_user_settings

from settings import (
    DISCOVERY_PORT,
    DISCOVERY_INTERVAL,
)

from ..utils import get_broadcast_addresses

from .peers import (
    DISCOVERY_PACKET_TYPE,
    MULTICAST_GROUP,
    MULTICAST_TTL,
    build_discovery_packet,
    add_or_update_peer,
)


# =========================
# PLATFORM HELPERS
# =========================

def is_android_runtime():
    """
    Возвращает True, если приложение запущено внутри Android/Chaquopy.

    Важно:
    - Chaquopy обычно запускает Python как Linux, поэтому одного platform.system()
      недостаточно.
    - android_server.py выставляет LANP2PCHAT_DATA_DIR / LANP2PCHAT_STATIC_DIR.
    """
    if os.environ.get("LANP2PCHAT_DATA_DIR"):
        return True

    if os.environ.get("LANP2PCHAT_STATIC_DIR"):
        return True

    try:
        system_name = platform.system().lower()
        if "android" in system_name:
            return True
    except Exception:
        pass

    return False


def get_discovery_modes_for_announce():
    """
    Какие способы отправки discovery использовать.

    ПК:
    - multicast
    - broadcast

    Android:
    - только multicast

    Так мы не ломаем мобильную часть и одновременно даём ПК два независимых
    способа найти друг друга в проблемных LAN-сетях.
    """
    if is_android_runtime():
        return ["multicast"]

    return ["multicast", "broadcast"]


# =========================
# DISCOVERY SOCKET HELPERS
# =========================

def create_discovery_send_socket():
    """
    UDP socket для отправки discovery hello-пакетов.

    На ПК через этот один socket отправляем одновременно:
    - multicast на MULTICAST_GROUP;
    - broadcast на 255.255.255.255 и directed broadcast адреса интерфейсов.

    На Android отправляем только multicast.
    """
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    except Exception:
        pass

    try:
        udp.setsockopt(
            socket.IPPROTO_IP,
            socket.IP_MULTICAST_TTL,
            int(MULTICAST_TTL),
        )
    except Exception:
        pass

    try:
        # Не отключаем loopback полностью: когда несколько клиентов запущены
        # на одном ПК для теста, это помогает им видеть discovery-пакеты.
        udp.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
    except Exception:
        pass

    return udp


def create_discovery_listen_socket():
    """
    UDP socket для приёма discovery-пакетов.

    Один socket слушает:
    - multicast-группу MULTICAST_GROUP;
    - broadcast-пакеты на DISCOVERY_PORT.

    Даже если multicast join не получится, socket всё равно останется слушать
    broadcast на 0.0.0.0:DISCOVERY_PORT.
    """
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except Exception:
        pass

    try:
        udp.bind(("", DISCOVERY_PORT))
    except Exception as e:
        print("[DISCOVERY LISTEN BIND ERROR]", e)
        udp.close()
        return None

    try:
        membership = socket.inet_aton(MULTICAST_GROUP) + socket.inet_aton("0.0.0.0")
        udp.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, membership)
    except Exception as e:
        # Не считаем это критичной ошибкой: broadcast всё равно будет работать.
        print("[DISCOVERY MULTICAST JOIN WARNING]", e)

    udp.setblocking(False)
    return udp


# =========================
# DISCOVERY SEND HELPERS
# =========================

def send_multicast_packet(udp, data):
    try:
        udp.sendto(data, (MULTICAST_GROUP, DISCOVERY_PORT))
        return True
    except Exception as e:
        print("[DISCOVERY MULTICAST SEND WARNING]", e)
        return False


def send_broadcast_packet(udp, data):
    ok = False
    broadcast_addresses = get_broadcast_addresses()

    for broadcast_ip in broadcast_addresses:
        try:
            udp.sendto(data, (broadcast_ip, DISCOVERY_PORT))
            ok = True
        except Exception as e:
            print(
                f"[DISCOVERY BROADCAST SEND WARNING] "
                f"ip={broadcast_ip} error={e}"
            )

    return ok


# =========================
# DISCOVERY LOOPS
# =========================

async def discovery_announce_loop():
    """
    Отправляет discovery hello-пакеты.

    ПК:
    - multicast и broadcast параллельно на каждом heartbeat.

    Android:
    - только multicast.

    Если один способ не проходит в конкретной сети, второй может сработать.
    """
    udp = create_discovery_send_socket()

    try:
        while True:
            try:
                config = await get_user_settings()
                packet = build_discovery_packet(config)
                data = json.dumps(packet, ensure_ascii=False).encode("utf-8")

                modes = get_discovery_modes_for_announce()

                if "multicast" in modes:
                    send_multicast_packet(udp, data)

                if "broadcast" in modes:
                    send_broadcast_packet(udp, data)

            except Exception as e:
                print("[DISCOVERY ANNOUNCE ERROR]", e)

            await asyncio.sleep(DISCOVERY_INTERVAL)

    finally:
        udp.close()


async def discovery_broadcast_loop():
    """
    Старое имя оставлено для совместимости.
    Теперь внутри может работать и multicast, и broadcast.
    """
    await discovery_announce_loop()


async def discovery_listen_loop():
    """
    Принимает UDP discovery-пакеты.

    Один loop принимает и multicast, и broadcast, потому что оба приходят
    на один порт DISCOVERY_PORT.
    """
    udp = create_discovery_listen_socket()

    if not udp:
        return

    loop = asyncio.get_running_loop()

    try:
        while True:
            try:
                data, addr = await loop.sock_recvfrom(udp, 4096)

                try:
                    packet = json.loads(data.decode("utf-8"))
                except Exception:
                    continue

                if packet.get("type") != DISCOVERY_PACKET_TYPE:
                    continue

                source_ip = addr[0] if addr else None

                add_or_update_peer(
                    packet,
                    source_ip,
                    source="udp_discovery",
                )

            except asyncio.CancelledError:
                break

            except Exception as e:
                print("[DISCOVERY LISTEN ERROR]", e)
                await asyncio.sleep(0.1)

    finally:
        udp.close()

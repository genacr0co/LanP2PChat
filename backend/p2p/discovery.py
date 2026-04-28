import json
import socket
import struct
import asyncio

from async_user_database import get_user_settings

from settings import (
    DISCOVERY_PORT,
    DISCOVERY_INTERVAL,
)

from ..utils import get_local_ip, get_broadcast_addresses

from .peers import (
    DISCOVERY_PACKET_TYPE,
    MULTICAST_GROUP,
    MULTICAST_TTL,
    build_discovery_packet,
    add_or_update_peer,
)


# =========================
# DISCOVERY SOCKET HELPERS
# =========================

def create_discovery_send_socket():
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    try:
        udp.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, MULTICAST_TTL)
    except Exception:
        pass

    try:
        udp.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
    except Exception:
        pass

    try:
        local_ip = get_local_ip()
        if local_ip and local_ip != "127.0.0.1":
            udp.setsockopt(
                socket.IPPROTO_IP,
                socket.IP_MULTICAST_IF,
                socket.inet_aton(local_ip),
            )
    except Exception:
        pass

    return udp


def create_discovery_listen_socket():
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

    # Подключаемся к multicast-группе.
    # Важно: на Android этого мало — ещё нужен MulticastLock на Java/Kotlin стороне.
    try:
        mreq = struct.pack(
            "4s4s",
            socket.inet_aton(MULTICAST_GROUP),
            socket.inet_aton("0.0.0.0"),
        )
        udp.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    except Exception as e:
        print("[DISCOVERY MULTICAST JOIN WARNING]", e)

    udp.setblocking(False)
    return udp


# =========================
# DISCOVERY LOOPS
# =========================

async def discovery_announce_loop():
    """
    Отправляет discovery-пакеты двумя способами:

    1. UDP multicast — основной способ для нормального LAN discovery.
    2. UDP broadcast — fallback для сетей/роутеров, где multicast нестабилен.

    Android всё равно должен держать WifiManager.MulticastLock,
    иначе система может фильтровать multicast/broadcast пакеты.
    """
    udp = create_discovery_send_socket()

    try:
        while True:
            try:
                config = await get_user_settings()
                packet = build_discovery_packet(config)
                data = json.dumps(packet, ensure_ascii=False).encode("utf-8")

                # Multicast announcement
                try:
                    udp.sendto(data, (MULTICAST_GROUP, DISCOVERY_PORT))
                except Exception as e:
                    print("[DISCOVERY MULTICAST SEND WARNING]", e)

                # Broadcast fallback
                for broadcast_ip in get_broadcast_addresses():
                    try:
                        udp.sendto(data, (broadcast_ip, DISCOVERY_PORT))
                    except Exception:
                        pass

            except Exception as e:
                print("[DISCOVERY ANNOUNCE ERROR]", e)

            await asyncio.sleep(DISCOVERY_INTERVAL)

    finally:
        udp.close()


async def discovery_broadcast_loop():
    """
    Старое имя оставлено для совместимости.
    Теперь внутри это общий announce loop:
    multicast + broadcast fallback.
    """
    await discovery_announce_loop()


async def discovery_listen_loop():
    """
    Один listener принимает и multicast, и broadcast discovery-пакеты.
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

                # addr[0] надёжнее, чем packet["ip"],
                # потому что это реальный IP отправителя в LAN.
                source_ip = addr[0] if addr else None

                # Пока невозможно точно узнать, пришёл пакет через multicast или broadcast,
                # потому что один socket принимает оба типа.
                # Но для логики это не важно: peer найден.
                add_or_update_peer(packet, source_ip, source="discovery")

            except asyncio.CancelledError:
                break

            except Exception as e:
                print("[DISCOVERY LISTEN ERROR]", e)
                await asyncio.sleep(0.1)

    finally:
        udp.close()
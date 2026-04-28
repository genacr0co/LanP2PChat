import json
import socket
import asyncio

from async_user_database import get_user_settings

from settings import (
    DISCOVERY_PORT,
    DISCOVERY_INTERVAL,
)

from ..utils import get_broadcast_addresses

from .peers import (
    DISCOVERY_PACKET_TYPE,
    build_discovery_packet,
    add_or_update_peer,
)


# =========================
# BROADCAST DISCOVERY SOCKET HELPERS
# =========================

def create_discovery_send_socket():
    """
    UDP socket для отправки broadcast hello-пакетов.

    Сейчас используем только broadcast:
    - 255.255.255.255
    - broadcast-адреса сетевых интерфейсов, если они доступны
    """
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    return udp


def create_discovery_listen_socket():
    """
    UDP socket для приёма broadcast discovery-пакетов.

    Важно:
    - multicast тут больше не используется;
    - IP_ADD_MEMBERSHIP больше не нужен;
    - слушаем просто 0.0.0.0:DISCOVERY_PORT.
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

    udp.setblocking(False)
    return udp


# =========================
# BROADCAST DISCOVERY LOOPS
# =========================

async def discovery_announce_loop():
    """
    Отправляет discovery hello-пакеты через UDP broadcast.

    Multicast временно полностью отключён,
    чтобы проверить старую простую схему:

    устройство -> broadcast -> другие устройства в LAN
    """
    udp = create_discovery_send_socket()

    try:
        while True:
            try:
                config = await get_user_settings()
                packet = build_discovery_packet(config)
                data = json.dumps(packet, ensure_ascii=False).encode("utf-8")

                broadcast_addresses = get_broadcast_addresses()

                for broadcast_ip in broadcast_addresses:
                    try:
                        udp.sendto(data, (broadcast_ip, DISCOVERY_PORT))
                    except Exception as e:
                        print(
                            f"[DISCOVERY BROADCAST SEND WARNING] "
                            f"ip={broadcast_ip} error={e}"
                        )

            except Exception as e:
                print("[DISCOVERY ANNOUNCE ERROR]", e)

            await asyncio.sleep(DISCOVERY_INTERVAL)

    finally:
        udp.close()


async def discovery_broadcast_loop():
    """
    Старое имя оставлено для совместимости.
    """
    await discovery_announce_loop()


async def discovery_listen_loop():
    """
    Принимает UDP broadcast discovery-пакеты.
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
                    source="broadcast",
                )

            except asyncio.CancelledError:
                break

            except Exception as e:
                print("[DISCOVERY LISTEN ERROR]", e)
                await asyncio.sleep(0.1)

    finally:
        udp.close()
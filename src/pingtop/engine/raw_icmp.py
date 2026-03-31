from __future__ import annotations

import asyncio
import ipaddress
import os
import socket
import struct
import time

from pingtop.models import PingResult

ICMP_ECHO_REQUEST = 8


def checksum(source_bytes: bytes) -> int:
    total = 0
    count_to = (len(source_bytes) // 2) * 2
    for count in range(0, count_to, 2):
        total += source_bytes[count + 1] * 256 + source_bytes[count]
        total &= 0xFFFFFFFF
    if count_to < len(source_bytes):
        total += source_bytes[-1]
        total &= 0xFFFFFFFF
    total = (total >> 16) + (total & 0xFFFF)
    total += total >> 16
    answer = ~total & 0xFFFF
    return answer >> 8 | ((answer << 8) & 0xFF00)


async def receive_one_ping(
    loop: asyncio.AbstractEventLoop, sock: socket.socket, packet_id: int, timeout: float
) -> float | None:
    deadline = loop.time() + timeout
    while True:
        remaining = deadline - loop.time()
        if remaining <= 0:
            return None
        try:
            received_packet = await asyncio.wait_for(loop.sock_recv(sock, 1024), remaining)
        except TimeoutError:
            return None
        time_received = time.time()
        icmp_header = received_packet[20:28]
        _type, _code, _checksum, this_packet_id, _sequence = struct.unpack(
            "bbHHh", icmp_header
        )
        if this_packet_id == packet_id:
            bytes_size = struct.calcsize("d")
            time_sent = struct.unpack("d", received_packet[28 : 28 + bytes_size])[0]
            return time_received - time_sent


async def send_one_ping(
    loop: asyncio.AbstractEventLoop,
    sock: socket.socket,
    resolved_ip: str,
    packet_id: int,
    packet_size: int,
) -> None:
    my_checksum = 0
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, my_checksum, packet_id, 1)
    bytes_size = struct.calcsize("d")
    data = (packet_size - bytes_size) * b"Q"
    data = struct.pack("d", time.time()) + data
    my_checksum = checksum(header + data)
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, socket.htons(my_checksum), packet_id, 1)
    sock.connect((resolved_ip, 1))
    await loop.sock_sendall(sock, header + data)


class RawIcmpEngine:
    async def ping_once(
        self, target: str, timeout: float, packet_size: int, flag: int
    ) -> PingResult:
        loop = asyncio.get_running_loop()
        try:
            resolved_ip = await self._resolve_target(loop, target)
        except socket.gaierror as exc:
            return PingResult(success=False, error_message=str(exc))

        icmp_proto = socket.getprotobyname("icmp")
        try:
            if os.getuid() != 0:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, icmp_proto)
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, icmp_proto)
        except OSError as exc:
            return PingResult(success=False, resolved_ip=resolved_ip, error_message=str(exc))

        sock.setblocking(False)
        packet_id = (os.getpid() & 0xFF00) | (flag & 0x00FF)
        try:
            await send_one_ping(loop, sock, resolved_ip, packet_id, packet_size)
            delay = await receive_one_ping(loop, sock, packet_id, timeout)
        except OSError as exc:
            return PingResult(success=False, resolved_ip=resolved_ip, error_message=str(exc))
        finally:
            sock.close()
        if delay is None:
            return PingResult(success=False, resolved_ip=resolved_ip)
        return PingResult(success=True, rtt_ms=delay * 1000, resolved_ip=resolved_ip)

    async def _resolve_target(
        self, loop: asyncio.AbstractEventLoop, target: str
    ) -> str:
        try:
            return str(ipaddress.ip_address(target))
        except ValueError:
            pass
        infos = await loop.getaddrinfo(
            target,
            None,
            family=socket.AF_INET,
            type=socket.SOCK_DGRAM,
        )
        if not infos:
            raise socket.gaierror(f"Unable to resolve {target}")
        return str(infos[0][4][0])

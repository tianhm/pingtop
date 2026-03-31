from __future__ import annotations

import os
import select
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


def receive_one_ping(sock: socket.socket, packet_id: int, timeout: float) -> float | None:
    time_left = timeout
    while True:
        started_select = time.time()
        ready = select.select([sock], [], [], time_left)
        how_long = time.time() - started_select
        if ready[0] == []:
            return None
        time_received = time.time()
        received_packet, _ = sock.recvfrom(1024)
        icmp_header = received_packet[20:28]
        _type, _code, _checksum, this_packet_id, _sequence = struct.unpack(
            "bbHHh", icmp_header
        )
        if this_packet_id == packet_id:
            bytes_size = struct.calcsize("d")
            time_sent = struct.unpack("d", received_packet[28 : 28 + bytes_size])[0]
            return time_received - time_sent
        time_left -= how_long
        if time_left <= 0:
            return None


def send_one_ping(sock: socket.socket, dest_addr: str, packet_id: int, packet_size: int) -> None:
    resolved_ip = socket.gethostbyname(dest_addr)
    my_checksum = 0
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, my_checksum, packet_id, 1)
    bytes_size = struct.calcsize("d")
    data = (packet_size - bytes_size) * b"Q"
    data = struct.pack("d", time.time()) + data
    my_checksum = checksum(header + data)
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, socket.htons(my_checksum), packet_id, 1)
    sock.sendto(header + data, (resolved_ip, 1))


class RawIcmpEngine:
    def ping_once(self, target: str, timeout: float, packet_size: int, flag: int) -> PingResult:
        try:
            resolved_ip = socket.gethostbyname(target)
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

        packet_id = (os.getpid() & 0xFF00) | (flag & 0x00FF)
        try:
            send_one_ping(sock, target, packet_id, packet_size)
            delay = receive_one_ping(sock, packet_id, timeout)
        except OSError as exc:
            return PingResult(success=False, resolved_ip=resolved_ip, error_message=str(exc))
        finally:
            sock.close()
        if delay is None:
            return PingResult(success=False, resolved_ip=resolved_ip)
        return PingResult(success=True, rtt_ms=delay * 1000, resolved_ip=resolved_ip)


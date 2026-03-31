from __future__ import annotations

from typing import cast

from pingtop.models import SessionSnapshot


def render_summary(snapshot: SessionSnapshot) -> str:
    blocks: list[str] = []
    for host in snapshot.hosts:
        hostname = str(host["target"])
        error = host["last_error"]
        if host["seq"] == 0 and error and error != "timeout":
            blocks.append(
                f"--- {hostname} ping statistics ---\n"
                f"ping: cannot resolve {hostname}: {error}"
            )
            continue
        seq = int(cast(int, host["seq"]))
        lost = int(cast(int, host["lost"]))
        received = seq - lost
        packet_lost = (lost / seq * 100) if seq else 0.0
        summary = (
            f"--- {hostname} ping statistics ---\n"
            f"{seq} packets transmitted, {received} packets received, "
            f"{packet_lost:.1f}% packet loss"
        )
        if host["min_rtt_ms"] is not None:
            summary += (
                "\nround-trip min/avg/max/stddev = "
                f"{float(cast(float, host['min_rtt_ms'])):.2f}/"
                f"{float(cast(float, host['avg_rtt_ms'])):.2f}/"
                f"{float(cast(float, host['max_rtt_ms'])):.2f}/"
                f"{float(cast(float, host['stddev_ms'] or 0.0)):.2f} ms"
            )
        blocks.append(summary)
    return "\n\n".join(blocks)

from __future__ import annotations

from pingtop.models import PingResult, SessionConfig
from pingtop.session import PingSession
from pingtop.summary import render_summary


def test_render_summary_success_and_error() -> None:
    session = PingSession(SessionConfig(), ["1.1.1.1", "bad-host"])
    host_ids = list(session.hosts)

    session.apply_result(host_ids[0], PingResult(success=True, rtt_ms=10.0, resolved_ip="1.1.1.1"))
    session.apply_result(host_ids[0], PingResult(success=False, resolved_ip="1.1.1.1"))
    session.apply_result(host_ids[1], PingResult(success=False, error_message="Unknown host"))

    summary = render_summary(session.snapshot())

    assert "--- 1.1.1.1 ping statistics ---" in summary
    assert "2 packets transmitted, 1 packets received, 50.0% packet loss" in summary
    assert "round-trip min/avg/max/stddev = 10.00/10.00/10.00/0.00 ms" in summary
    assert "ping: cannot resolve bad-host: Unknown host" in summary


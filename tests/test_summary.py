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

    assert summary.splitlines()[0] == "ERR | 2 hosts | tx 2 | rx 1 | loss 50.0% | err 1 | lossy 1"
    assert "ERR bad-host Unknown host" in summary
    assert "LOSS 1.1.1.1 50.0% loss (1/2), avg 10.0 ms" in summary


def test_render_summary_stays_short_for_healthy_hosts() -> None:
    session = PingSession(SessionConfig(), ["1.1.1.1", "8.8.8.8"])
    for host_id, ip in zip(session.hosts, ["1.1.1.1", "8.8.8.8"], strict=True):
        session.apply_result(host_id, PingResult(success=True, rtt_ms=10.0, resolved_ip=ip))

    summary = render_summary(session.snapshot())

    assert summary == "OK | 2 hosts | tx 2 | rx 2 | loss 0.0%"


def test_render_summary_limits_issue_lines() -> None:
    session = PingSession(
        SessionConfig(),
        ["bad-1", "bad-2", "bad-3", "bad-4", "bad-5", "bad-6", "bad-7"],
    )
    for host_id in session.hosts:
        session.apply_result(host_id, PingResult(success=False, error_message="Unknown host"))

    summary = render_summary(session.snapshot(), max_issues=5)

    assert summary.count("\n") == 6
    assert "MORE +2 more issues" in summary

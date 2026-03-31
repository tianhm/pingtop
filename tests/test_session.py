from __future__ import annotations

from pingtop.models import PingResult, SessionConfig, SortKey
from pingtop.session import PingSession


def build_session(*targets: str) -> PingSession:
    return PingSession(SessionConfig(), targets)


def test_add_edit_delete_and_select_host() -> None:
    session = build_session("1.1.1.1")
    host_id = next(iter(session.hosts))

    added_id = session.add_host("8.8.8.8")
    assert added_id in session.hosts

    session.edit_host(added_id, "9.9.9.9")
    assert session.hosts[added_id].config.target == "9.9.9.9"

    session.select(added_id)
    assert session.current_host() is session.hosts[added_id]

    session.delete_host(host_id)
    assert host_id not in session.hosts


def test_pause_resume_reset_and_aggregate_updates() -> None:
    session = build_session("1.1.1.1")
    host_id = next(iter(session.hosts))

    session.apply_result(host_id, PingResult(success=True, rtt_ms=11.5, resolved_ip="1.1.1.1"))
    session.apply_result(host_id, PingResult(success=False, resolved_ip="1.1.1.1"))
    row = session.host_snapshot(host_id)

    assert row["seq"] == 2
    assert row["lost"] == 1
    assert row["trend"]

    session.pause_host(host_id)
    assert session.hosts[host_id].paused is True

    session.resume_host(host_id)
    assert session.hosts[host_id].paused is False

    session.reset_host(host_id)
    reset_row = session.host_snapshot(host_id)
    assert reset_row["seq"] == 0
    assert reset_row["lost"] == 0
    assert reset_row["trend"] == ""


def test_cycle_and_toggle_sort() -> None:
    session = build_session("b.example", "a.example")

    assert session.sort_key == SortKey.HOST
    session.cycle_sort()
    assert session.sort_key == SortKey.IP

    session.toggle_sort_order()
    assert session.sort_reverse is True


def test_dotted_host_sort_uses_numeric_segments() -> None:
    session = build_session("1.1.1.10", "1.1.1.6", "1.1.1.9", "1.1.1.7")

    rows = session.host_snapshots()

    assert [row["target"] for row in rows] == [
        "1.1.1.6",
        "1.1.1.7",
        "1.1.1.9",
        "1.1.1.10",
    ]

    session.set_sort(SortKey.HOST, reverse=True)
    rows = session.host_snapshots()

    assert [row["target"] for row in rows] == [
        "1.1.1.10",
        "1.1.1.9",
        "1.1.1.7",
        "1.1.1.6",
    ]

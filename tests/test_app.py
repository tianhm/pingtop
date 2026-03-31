from __future__ import annotations

from collections import defaultdict

import pytest

from pingtop.app import PingTopApp
from pingtop.models import PingResult, SessionConfig
from pingtop.session import PingSession
from pingtop.widgets.host_table import HostTable


class FakeEngine:
    def __init__(self) -> None:
        self._counts = defaultdict(int)

    def ping_once(self, target: str, timeout: float, packet_size: int, flag: int) -> PingResult:
        self._counts[target] += 1
        count = self._counts[target]
        if target == "bad-host":
            return PingResult(success=False, error_message="Unknown host")
        if count % 3 == 0:
            return PingResult(success=False, resolved_ip="127.0.0.1")
        return PingResult(success=True, rtt_ms=10.0 + count, resolved_ip="127.0.0.1")


@pytest.mark.asyncio
async def test_app_boots_and_updates_rows() -> None:
    session = PingSession(SessionConfig(interval=0.05, timeout=0.01), ["1.1.1.1"])
    app = PingTopApp(session=session, engine=FakeEngine())

    async with app.run_test() as pilot:
        await pilot.pause(0.25)
        row = session.host_snapshot(next(iter(session.hosts)))
        assert row["seq"] >= 1
        assert row["trend"]
        await pilot.press("q")


@pytest.mark.asyncio
async def test_app_host_lifecycle_actions() -> None:
    session = PingSession(SessionConfig(interval=0.05, timeout=0.01), ["1.1.1.1"])
    app = PingTopApp(session=session, engine=FakeEngine())

    async with app.run_test() as pilot:
        await pilot.pause(0.1)
        app._handle_add_host("8.8.8.8")
        await pilot.pause(0.1)
        assert len(session.hosts) == 2

        selected = session.selected_host_id
        assert selected is not None
        app._handle_edit_host(selected, "9.9.9.9")
        assert session.hosts[selected].config.target == "9.9.9.9"

        app.action_toggle_selected_pause()
        assert session.hosts[selected].paused is True

        app.action_toggle_selected_pause()
        assert session.hosts[selected].paused is False

        app.action_reset_selected()
        assert session.hosts[selected].stats.seq == 0

        app._handle_delete_host(selected, True)
        assert selected not in session.hosts
        await pilot.press("q")


@pytest.mark.asyncio
async def test_app_sort_and_help_screen() -> None:
    session = PingSession(SessionConfig(interval=0.05, timeout=0.01), ["1.1.1.1", "bad-host"])
    app = PingTopApp(session=session, engine=FakeEngine())

    async with app.run_test() as pilot:
        await pilot.pause(0.15)
        app.action_cycle_sort()
        app.action_toggle_sort_order()
        assert session.sort_reverse is True
        app.action_show_help()
        await pilot.pause(0.05)
        assert app.screen_stack
        table = app.query_one(HostTable)
        assert table.row_count == len(session.hosts)
        await pilot.press("q")


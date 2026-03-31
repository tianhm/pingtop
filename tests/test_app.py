from __future__ import annotations

from collections import defaultdict

import pytest
from rich.text import Text

from pingtop.app import PingTopApp
from pingtop.models import PingResult, SessionConfig, SortKey
from pingtop.session import PingSession
from pingtop.widgets.details_panel import DetailsPanel
from pingtop.widgets.host_table import HostTable


class FakeEngine:
    def __init__(self) -> None:
        self._counts = defaultdict(int)

    async def ping_once(
        self, target: str, timeout: float, packet_size: int, flag: int
    ) -> PingResult:
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

    async with app.run_test(size=(160, 40)) as pilot:
        await pilot.pause(0.25)
        table = app.query_one(HostTable)
        row = session.host_snapshot(next(iter(session.hosts)))
        assert row["seq"] >= 1
        assert row["trend"]
        trend_index = HostTable.COLUMN_PROFILES["wide"].index("trend")
        trend_cell = table.get_row(str(row["id"]))[trend_index]
        assert isinstance(trend_cell, Text)
        assert trend_cell.spans
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
        await pilot.press("S")
        await pilot.pause(0.05)
        assert session.sort_key.value == "seq"
        assert session.sort_reverse is False
        await pilot.press("S")
        await pilot.pause(0.05)
        assert session.sort_reverse is True
        await pilot.press("h")
        await pilot.pause(0.05)
        assert app.screen_stack
        await pilot.press("h")
        await pilot.pause(0.05)
        table = app.query_one(HostTable)
        assert table.row_count == len(session.hosts)
        await pilot.press("q")


@pytest.mark.asyncio
async def test_table_keeps_numeric_width_and_shows_sort_indicator() -> None:
    session = PingSession(SessionConfig(interval=0.05, timeout=0.01), ["1.1.1.1"])
    app = PingTopApp(session=session, engine=FakeEngine())

    async with app.run_test(size=(160, 40)) as pilot:
        table = app.query_one(HostTable)
        session.set_sort(session.sort_key, reverse=False)
        app._sync_all_rows()

        row = session.host_snapshot(next(iter(session.hosts)))
        row["seq"] = 318
        table.upsert_host(row)
        wide_value = table.get_row(str(row["id"]))[2]

        row["seq"] = 99
        table.upsert_host(row)
        narrow_value = table.get_row(str(row["id"]))[2]

        host_header = str(table.ordered_columns[0].label)
        assert host_header.endswith("▲")
        assert len(str(wide_value)) == len(str(narrow_value))
        assert str(narrow_value).strip() == "99"
        await pilot.press("q")


@pytest.mark.asyncio
async def test_details_panel_defaults_open_on_large_window_and_closed_on_small_window() -> None:
    large_session = PingSession(SessionConfig(interval=0.05, timeout=0.01), ["1.1.1.1"])
    large_app = PingTopApp(session=large_session, engine=FakeEngine())
    async with large_app.run_test(size=(160, 40)) as pilot:
        details = large_app.query_one(DetailsPanel)
        table = large_app.query_one(HostTable)
        assert not details.has_class("hidden-panel")
        assert len(table.ordered_columns) == len(HostTable.COLUMN_PROFILES["wide"])
        await pilot.press("q")

    small_session = PingSession(SessionConfig(interval=0.05, timeout=0.01), ["1.1.1.1"])
    small_app = PingTopApp(session=small_session, engine=FakeEngine())
    async with small_app.run_test(size=(90, 24)) as pilot:
        details = small_app.query_one(DetailsPanel)
        table = small_app.query_one(HostTable)
        assert details.has_class("hidden-panel")
        assert len(table.ordered_columns) == len(HostTable.COLUMN_PROFILES["narrow"])
        await pilot.press("i")
        await pilot.pause(0.05)
        assert not details.has_class("hidden-panel")
        await pilot.press("q")


@pytest.mark.asyncio
async def test_sync_rows_preserves_scroll_position() -> None:
    hosts = [f"10.0.0.{index}" for index in range(1, 41)]
    session = PingSession(SessionConfig(interval=0.05, timeout=0.01), hosts)
    app = PingTopApp(session=session, engine=FakeEngine())

    async with app.run_test(size=(90, 12)) as pilot:
        table = app.query_one(HostTable)
        await pilot.pause(0.1)
        table.scroll_to(y=8, immediate=True)
        await pilot.pause(0.05)
        before = table.scroll_y

        session.set_sort(SortKey.SEQ, reverse=False)
        total_hosts = len(session.hosts)
        for index, record in enumerate(session.hosts.values(), start=1):
            record.stats.seq = total_hosts - index
        app._sync_all_rows()
        await pilot.pause(0.05)

        assert before > 0
        assert table.scroll_y == pytest.approx(before)
        await pilot.press("q")

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass
from typing import cast

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Footer, Header, Static
from textual.worker import Worker, get_current_worker

from pingtop.models import HostId, PingEngine, PingResult
from pingtop.screens.host_form import ConfirmScreen, HelpScreen, HostFormScreen
from pingtop.session import PingSession
from pingtop.widgets.details_panel import DetailsPanel
from pingtop.widgets.host_table import HostTable

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PendingUpdate:
    host_id: HostId
    result: PingResult


class PingSample(Message):
    def __init__(self, host_id: HostId, result: PingResult) -> None:
        self.host_id = host_id
        self.result = result
        super().__init__()


class PingTopApp(App[None]):
    CSS_PATH = "app.tcss"
    BINDINGS = [
        Binding("q", "quit_session", "Quit"),
        Binding("a", "add_host", "Add"),
        Binding("e", "edit_selected", "Edit"),
        Binding("d", "delete_selected", "Delete"),
        Binding("space", "toggle_selected_pause", "Pause"),
        Binding("p", "toggle_all_pause", "Pause All"),
        Binding("r", "reset_selected", "Reset"),
        Binding("shift+r", "reset_all", "Reset All"),
        Binding("s", "cycle_sort", "Sort"),
        Binding("shift+s", "toggle_sort_order", "Reverse"),
        Binding("enter", "focus_details", "Details"),
        Binding("tab", "focus_next"),
        Binding("?", "show_help", "Help", show=False),
    ]

    def __init__(self, session: PingSession, engine: PingEngine) -> None:
        super().__init__()
        self.session = session
        self.engine = engine
        self._ping_workers: dict[HostId, Worker[None]] = {}
        self._pending_updates: deque[PendingUpdate] = deque()
        self._last_sort_refresh = 0.0

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main-pane"):
            yield HostTable(id="host-table")
            yield DetailsPanel(id="details-panel")
        yield Static("", id="status-strip")
        yield Footer()

    def on_mount(self) -> None:
        self.table = self.query_one(HostTable)
        self.details = self.query_one(DetailsPanel)
        self.status_strip = self.query_one("#status-strip", Static)
        self._sync_all_rows()
        self._refresh_selected_details()
        self._refresh_status_strip()
        self.set_interval(0.25, self.flush_updates)
        for host_id in list(self.session.hosts):
            self._start_worker(host_id)
        if self.session.selected_host_id:
            self.table.select_host(self.session.selected_host_id)

    def on_unmount(self) -> None:
        self._stop_all_workers()

    @on(HostTable.RowHighlighted)
    def on_row_highlighted(self, event: HostTable.RowHighlighted) -> None:
        row_key = event.row_key.value if event.row_key else None
        self.session.select(str(row_key) if row_key is not None else None)
        self._refresh_selected_details()

    def action_focus_next(self) -> None:
        if self.focused is self.table:
            self.details.focus()
        else:
            self.table.focus()

    def action_focus_details(self) -> None:
        self.details.focus()

    def action_show_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_quit_session(self) -> None:
        self._stop_all_workers()
        self.exit()

    def action_add_host(self) -> None:
        self.push_screen(HostFormScreen("Add host"), self._handle_add_host)

    def action_edit_selected(self) -> None:
        record = self.session.current_host()
        if record is None:
            self.notify("No host selected.", severity="warning")
            return
        self.push_screen(
            HostFormScreen("Edit host", value=record.config.target),
            lambda target: self._handle_edit_host(record.config.id, target),
        )

    def action_delete_selected(self) -> None:
        record = self.session.current_host()
        if record is None:
            self.notify("No host selected.", severity="warning")
            return
        self.push_screen(
            ConfirmScreen(f"Delete host '{record.config.target}'?"),
            lambda confirmed: self._handle_delete_host(record.config.id, confirmed),
        )

    def action_toggle_selected_pause(self) -> None:
        record = self.session.current_host()
        if record is None:
            self.notify("No host selected.", severity="warning")
            return
        self.session.toggle_host_pause(record.config.id)
        self._refresh_host(record.config.id)

    def action_toggle_all_pause(self) -> None:
        self.session.toggle_all_pause()
        for host_id in list(self.session.hosts):
            self._refresh_host(host_id)
        self._refresh_status_strip()
        self._refresh_selected_details()

    def action_reset_selected(self) -> None:
        record = self.session.current_host()
        if record is None:
            self.notify("No host selected.", severity="warning")
            return
        self.session.reset_host(record.config.id)
        self._refresh_host(record.config.id)

    def action_reset_all(self) -> None:
        self.session.reset_all()
        self._sync_all_rows()
        self._refresh_selected_details()
        self._refresh_status_strip()

    def action_cycle_sort(self) -> None:
        self.session.cycle_sort()
        self._sync_all_rows()
        self._refresh_status_strip()

    def action_toggle_sort_order(self) -> None:
        self.session.toggle_sort_order()
        self._sync_all_rows()

    @on(PingSample)
    def on_ping_sample(self, message: PingSample) -> None:
        self._pending_updates.append(PendingUpdate(message.host_id, message.result))

    def flush_updates(self) -> None:
        if not self._pending_updates:
            return
        touched: set[HostId] = set()
        while self._pending_updates:
            pending = self._pending_updates.popleft()
            if pending.host_id not in self.session.hosts:
                continue
            self.session.apply_result(pending.host_id, pending.result)
            touched.add(pending.host_id)
        for host_id in touched:
            self._refresh_host(host_id)
        if touched and (time.monotonic() - self._last_sort_refresh) >= 1.0:
            self._last_sort_refresh = time.monotonic()
            self._sync_all_rows()
        self._refresh_status_strip()
        self._refresh_selected_details()

    def _refresh_host(self, host_id: HostId) -> None:
        if host_id not in self.session.hosts:
            return
        self.table.upsert_host(self.session.host_snapshot(host_id))
        if self.session.selected_host_id == host_id:
            self._refresh_selected_details()
        self.table.select_host(self.session.selected_host_id)

    def _sync_all_rows(self) -> None:
        self.table.sync_rows(self.session.host_snapshots())
        self.table.select_host(self.session.selected_host_id)
        self._refresh_selected_details()

    def _refresh_selected_details(self) -> None:
        record = self.session.current_host()
        self.details.show_host(record.snapshot() if record else None)

    def _refresh_status_strip(self) -> None:
        aggregates = self.session.aggregates()
        self.status_strip.update(
            " | ".join(
                [
                    f"Hosts {aggregates['total_hosts']}",
                    f"Active {aggregates['active_hosts']}",
                    f"Paused {aggregates['paused_hosts']}",
                    f"Errors {aggregates['error_hosts']}",
                    f"Sent {aggregates['total_sent']}",
                    f"Lost {aggregates['total_lost']}",
                    f"Loss {float(cast(float, aggregates['loss_percent'])):.1f}%",
                    f"Sort {self.session.sort_key.value}",
                    "DESC" if self.session.sort_reverse else "ASC",
                ]
            )
        )

    def _handle_add_host(self, target: str | None) -> None:
        if target is None:
            return
        try:
            host_id = self.session.add_host(target)
        except ValueError as exc:
            self.notify(str(exc), severity="error")
            return
        self._start_worker(host_id)
        self._sync_all_rows()

    def _handle_edit_host(self, host_id: HostId, target: str | None) -> None:
        if target is None:
            return
        try:
            self.session.edit_host(host_id, target)
        except ValueError as exc:
            self.notify(str(exc), severity="error")
            return
        self._restart_worker(host_id)
        self._refresh_host(host_id)
        self._refresh_status_strip()

    def _handle_delete_host(self, host_id: HostId, confirmed: bool | None) -> None:
        if not confirmed:
            return
        self._stop_worker(host_id)
        self.session.delete_host(host_id)
        self.table.remove_host(host_id)
        self.table.select_host(self.session.selected_host_id)
        self._refresh_selected_details()
        self._refresh_status_strip()

    def _start_worker(self, host_id: HostId) -> None:
        if host_id in self._ping_workers:
            return
        self._ping_workers[host_id] = self._run_host_loop(host_id)

    def _restart_worker(self, host_id: HostId) -> None:
        self._stop_worker(host_id)
        self._start_worker(host_id)

    def _stop_worker(self, host_id: HostId) -> None:
        worker = self._ping_workers.pop(host_id, None)
        if worker is not None:
            worker.cancel()

    def _stop_all_workers(self) -> None:
        for host_id in list(self._ping_workers):
            self._stop_worker(host_id)

    @work(thread=True, group="ping-hosts", exclusive=False, exit_on_error=False)
    def _run_host_loop(self, host_id: HostId) -> None:
        worker = get_current_worker()
        flag = int(host_id[:2], 16)
        while not worker.is_cancelled:
            record = self.session.hosts.get(host_id)
            if record is None:
                return
            if record.paused:
                time.sleep(0.1)
                continue
            target = record.config.target
            result = self.engine.ping_once(
                target=target,
                timeout=self.session.config.timeout,
                packet_size=self.session.config.packet_size,
                flag=flag,
            )
            self.post_message(PingSample(host_id, result))
            self._sleep_with_cancel(self.session.config.interval, worker)

    @staticmethod
    def _sleep_with_cancel(interval: float, worker: Worker[None]) -> None:
        end_at = time.monotonic() + interval
        while not worker.is_cancelled:
            remaining = end_at - time.monotonic()
            if remaining <= 0:
                return
            time.sleep(min(0.1, remaining))

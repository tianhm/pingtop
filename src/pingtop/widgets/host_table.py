from __future__ import annotations

from typing import cast

from rich.text import Text
from textual.widgets import DataTable

from pingtop.models import SortKey


class HostTable(DataTable[str]):
    SORT_ASC = "▲"
    SORT_DESC = "▼"
    COLUMNS: list[tuple[str, str]] = [
        ("Host", "target"),
        ("IP", "resolved_ip"),
        ("Seq", "seq"),
        ("RTT", "last_rtt_ms"),
        ("Min", "min_rtt_ms"),
        ("Avg", "avg_rtt_ms"),
        ("Max", "max_rtt_ms"),
        ("StdDev", "stddev_ms"),
        ("Loss", "lost"),
        ("Loss%", "loss_percent"),
        ("State", "state"),
        ("Trend", "trend"),
    ]
    COLUMN_PROFILES: dict[str, list[str]] = {
        "wide": [
            "target",
            "resolved_ip",
            "seq",
            "last_rtt_ms",
            "min_rtt_ms",
            "avg_rtt_ms",
            "max_rtt_ms",
            "stddev_ms",
            "lost",
            "loss_percent",
            "state",
            "trend",
        ],
        "medium": [
            "target",
            "resolved_ip",
            "seq",
            "last_rtt_ms",
            "avg_rtt_ms",
            "loss_percent",
            "state",
            "trend",
        ],
        "narrow": [
            "target",
            "resolved_ip",
            "last_rtt_ms",
            "avg_rtt_ms",
            "loss_percent",
            "state",
        ],
    }
    STABLE_WIDTH_COLUMNS = {
        "seq",
        "last_rtt_ms",
        "min_rtt_ms",
        "avg_rtt_ms",
        "max_rtt_ms",
        "stddev_ms",
        "lost",
        "loss_percent",
    }

    def on_mount(self) -> None:
        self.cursor_type = "row"
        self.zebra_stripes = True
        self._column_labels = {key: label for label, key in self.COLUMNS}
        self._all_column_keys = [key for _, key in self.COLUMNS]
        self._active_column_keys: list[str] = []
        self._column_widths = {
            key: len(self._format_header(label, None))
            for label, key in self.COLUMNS
            if key in self.STABLE_WIDTH_COLUMNS
        }

    def upsert_host(self, row: dict[str, object]) -> None:
        row_key = str(row["id"])
        values = self._row_values(row)
        try:
            self.get_row(row_key)
        except KeyError:
            self.add_row(*values, key=row_key)
            return
        for key, value in zip(self._active_column_keys, values, strict=True):
            self.update_cell(row_key, key, value, update_width=False)

    def sync_rows(self, rows: list[dict[str, object]]) -> None:
        self.clear(columns=False)
        for row in rows:
            self.add_row(*self._row_values(row), key=str(row["id"]))

    def remove_host(self, host_id: str) -> None:
        try:
            self.remove_row(host_id)
        except KeyError:
            return

    def select_host(self, host_id: str | None) -> None:
        if not host_id:
            return
        try:
            row_index = self.get_row_index(host_id)
        except KeyError:
            return
        self.move_cursor(row=row_index, column=0, animate=False)

    def set_column_profile(self, profile: str) -> bool:
        column_keys = self.COLUMN_PROFILES[profile]
        if column_keys == self._active_column_keys:
            return False
        self.clear(columns=True)
        self.add_columns(
            *[
                (self._format_header(self._column_labels[key], None), key)
                for key in column_keys
            ]
        )
        self.fixed_columns = 1
        self._active_column_keys = list(column_keys)
        return True

    def set_sort_indicator(self, sort_key: SortKey, reverse: bool) -> None:
        current = sort_key.value
        for column in self.ordered_columns:
            column_key = str(column.key.value)
            base_label = self._column_labels[column_key]
            marker = None
            if column_key == current:
                marker = self.SORT_DESC if reverse else self.SORT_ASC
            column.label = Text(self._format_header(base_label, marker))
        self.refresh(layout=True)

    def _row_values(self, row: dict[str, object]) -> list[str]:
        return [
            self._format_value(column_key, row.get(column_key))
            for column_key in self._active_column_keys
        ]

    @staticmethod
    def _format_header(label: str, marker: str | None) -> str:
        return f"{label}{marker or ' '}"

    def _format_value(self, column_key: str, value: object) -> str:
        if value is None:
            rendered = ""
        elif column_key == "loss_percent":
            rendered = f"{float(cast(float, value)):.1f}%"
        elif column_key in {
            "last_rtt_ms",
            "min_rtt_ms",
            "avg_rtt_ms",
            "max_rtt_ms",
            "stddev_ms",
        }:
            rendered = f"{float(cast(float, value)):.1f}"
        else:
            rendered = str(value)
        if column_key in self.STABLE_WIDTH_COLUMNS:
            width = max(self._column_widths.get(column_key, 0), len(rendered))
            self._column_widths[column_key] = width
            return rendered.rjust(width)
        if column_key == "loss_percent":
            return rendered
        return rendered

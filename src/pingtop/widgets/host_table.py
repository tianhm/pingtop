from __future__ import annotations

from typing import cast

from rich.text import Text
from textual._two_way_dict import TwoWayDict
from textual.widgets import DataTable
from textual.widgets._data_table import ColumnKey, RowKey

from pingtop.models import SortKey
from pingtop.widgets.trend import render_trend


class HostTable(DataTable[object]):
    SORT_ASC = "▲"
    SORT_DESC = "▼"
    TREND_COLUMN_KEY = "trend"
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
        row_key = RowKey(str(row["id"]))
        values = self._row_values(row)
        if row_key not in self._row_locations:
            self.add_row(*values, key=str(row_key.value))
            self._resize_trend_column()
            return
        for key, value in zip(self._active_column_keys, values, strict=True):
            self.update_cell(row_key, key, value, update_width=False)
        self._resize_trend_column()

    def sync_rows(self, rows: list[dict[str, object]]) -> None:
        desired_keys = [RowKey(str(row["id"])) for row in rows]
        desired_set = set(desired_keys)
        for row_key in list(self._data):
            if row_key not in desired_set:
                self.remove_row(row_key)
        for row in rows:
            self.upsert_host(row)
        self._reorder_rows(desired_keys)
        self._resize_trend_column()

    def remove_host(self, host_id: str) -> None:
        try:
            self.remove_row(host_id)
        except KeyError:
            return

    def select_host(self, host_id: str | None, *, scroll: bool = True) -> None:
        if not host_id:
            return
        try:
            row_index = self.get_row_index(host_id)
        except KeyError:
            return
        self.move_cursor(row=row_index, column=0, animate=False, scroll=scroll)

    def set_column_profile(self, profile: str) -> bool:
        column_keys = self.COLUMN_PROFILES[profile]
        if column_keys == self._active_column_keys:
            self._resize_trend_column()
            return False
        self.clear(columns=True)
        for key in column_keys:
            self.add_column(
                self._format_header(self._column_labels[key], None),
                key=key,
                width=1 if key == self.TREND_COLUMN_KEY else None,
            )
        self.fixed_columns = 1
        self._active_column_keys = list(column_keys)
        self._resize_trend_column()
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

    def _row_values(self, row: dict[str, object]) -> list[object]:
        return [
            render_trend(
                cast(list[float | None] | None, row.get("history_ms")),
                width=self._trend_content_width(),
            )
            if column_key == self.TREND_COLUMN_KEY
            else self._format_value(column_key, row.get(column_key))
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

    def _reorder_rows(self, desired_keys: list[RowKey]) -> None:
        current_keys = [row.key for row in self.ordered_rows]
        if current_keys == desired_keys:
            return
        self._row_locations = TwoWayDict(
            {row_key: index for index, row_key in enumerate(desired_keys)}
        )
        self._update_count += 1
        self.refresh()

    def _trend_content_width(self) -> int | None:
        if self.TREND_COLUMN_KEY not in self._active_column_keys:
            return None
        column = self.columns.get(ColumnKey(self.TREND_COLUMN_KEY))
        if column is None:
            return None
        return max(1, column.width)

    def _resize_trend_column(self) -> None:
        available_width = self.scrollable_content_region.width
        if self.TREND_COLUMN_KEY not in self._active_column_keys or available_width <= 0:
            return
        trend_column = self.columns.get(ColumnKey(self.TREND_COLUMN_KEY))
        if trend_column is None:
            return
        reserved_width = sum(
            column.get_render_width(self)
            for column in self.ordered_columns
            if str(column.key.value) != self.TREND_COLUMN_KEY
        )
        target_width = max(
            len(self._format_header(self._column_labels[self.TREND_COLUMN_KEY], None)),
            available_width - reserved_width - (2 * self.cell_padding),
        )
        if trend_column.width == target_width and not trend_column.auto_width:
            return
        trend_column.width = target_width
        trend_column.auto_width = False
        self._require_update_dimensions = True
        self.refresh(layout=True)

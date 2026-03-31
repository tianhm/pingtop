from __future__ import annotations

from typing import cast

from textual.widgets import DataTable


class HostTable(DataTable[str]):
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

    def on_mount(self) -> None:
        self.cursor_type = "row"
        self.zebra_stripes = True
        self.add_columns(*[(label, key) for label, key in self.COLUMNS])
        self.fixed_columns = 1

    def upsert_host(self, row: dict[str, object]) -> None:
        row_key = str(row["id"])
        values = self._row_values(row)
        try:
            self.get_row(row_key)
        except KeyError:
            self.add_row(*values, key=row_key)
            return
        for key, value in zip(
            (column_key for _, column_key in self.COLUMNS), values, strict=True
        ):
            self.update_cell(row_key, key, value, update_width=True)

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

    def _row_values(self, row: dict[str, object]) -> list[str]:
        return [
            self._format_value(column_key, row.get(column_key))
            for _, column_key in self.COLUMNS
        ]

    @staticmethod
    def _format_value(column_key: str, value: object) -> str:
        if value is None:
            return ""
        if column_key == "loss_percent":
            return f"{float(cast(float, value)):.1f}%"
        if column_key in {"last_rtt_ms", "min_rtt_ms", "avg_rtt_ms", "max_rtt_ms", "stddev_ms"}:
            return f"{float(cast(float, value)):.1f}"
        return str(value)

from __future__ import annotations

from typing import cast

from textual.widgets import Static


class DetailsPanel(Static):
    DEFAULT_MESSAGE = "Select a host to inspect live statistics."

    def show_host(self, row: dict[str, object] | None) -> None:
        if row is None:
            self.update(self.DEFAULT_MESSAGE)
            return
        self.update(
            "\n".join(
                [
                    f"Host:     {row['target']}",
                    f"IP:       {row['resolved_ip'] or '-'}",
                    f"State:    {row['state']}",
                    f"Last RTT: {self._fmt(row['last_rtt_ms'])}",
                    f"Min RTT:  {self._fmt(row['min_rtt_ms'])}",
                    f"Avg RTT:  {self._fmt(row['avg_rtt_ms'])}",
                    f"Max RTT:  {self._fmt(row['max_rtt_ms'])}",
                    f"StdDev:   {self._fmt(row['stddev_ms'])}",
                    f"Sent:     {row['seq']}",
                    f"Lost:     {row['lost']} ({float(cast(float, row['loss_percent'])):.1f}%)",
                    f"Error:    {row['last_error'] or '-'}",
                    "",
                    "Trend",
                    str(row["trend"] or "-"),
                ]
            )
        )

    @staticmethod
    def _fmt(value: object) -> str:
        if value is None:
            return "-"
        return f"{float(cast(float, value)):.1f} ms"

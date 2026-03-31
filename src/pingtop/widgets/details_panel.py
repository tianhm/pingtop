from __future__ import annotations

from typing import cast

from rich.text import Text
from textual.widgets import Static

from pingtop.models import TIMEOUT_MARKER
from pingtop.widgets.trend import render_trend_graph


class DetailsPanel(Static):
    DEFAULT_MESSAGE = "Select a host to inspect live statistics."

    def show_host(self, row: dict[str, object] | None) -> None:
        if row is None:
            self.update(self.DEFAULT_MESSAGE)
            return
        history = cast(list[float | None], row["history_ms"])
        graph_width = self._graph_width()
        details = Text(
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
                    "Trend Graph",
                    self._trend_scale(history),
                    "oldest -> newest",
                ]
            )
            + "\n"
        )
        details.append_text(render_trend_graph(history, width=graph_width))
        self.update(details)

    @staticmethod
    def _fmt(value: object) -> str:
        if value is None:
            return "-"
        return f"{float(cast(float, value)):.1f} ms"

    def _graph_width(self) -> int:
        if self.size.width <= 0:
            return 32
        return max(12, min(48, self.size.width - 4))

    @staticmethod
    def _trend_scale(history: list[float | None]) -> str:
        samples = [sample for sample in history if sample is not None]
        if not samples:
            return "timeouts only"
        return f"low {min(samples):.1f} ms / high {max(samples):.1f} ms / timeout {TIMEOUT_MARKER}"

from __future__ import annotations

import math
from collections.abc import Sequence

from rich.text import Text

from pingtop.models import TIMEOUT_MARKER, TREND_BLOCKS, trend_cells

TREND_STYLES = (
    "#86efac",
    "#4ade80",
    "#a3e635",
    "#fde047",
    "#fb923c",
    "#f87171",
    "#ef4444",
    "#dc2626",
)
TIMEOUT_STYLE = "bold #ef4444"
DETAIL_GRAPH_EMPTY_STYLE = "#4b5563"


def render_trend(history: Sequence[float | None] | None, *, width: int | None = None) -> Text:
    if not history:
        return Text("-")
    trend = Text()
    cells = trend_cells(list(history))
    if width is not None and width > 0:
        cells = cells[-width:]
    for block, bucket in cells:
        style = TIMEOUT_STYLE if bucket is None else TREND_STYLES[bucket]
        trend.append(block, style=style)
    return trend


def render_trend_legend() -> Text:
    legend = Text()
    legend.append("Trend Legend\n")
    legend.append("low RTT ")
    for block, style in zip(TREND_BLOCKS, TREND_STYLES, strict=True):
        legend.append(f" {block} ", style=style)
    legend.append(" high RTT\n")
    legend.append("timeout ")
    legend.append(f" {TIMEOUT_MARKER} ", style=TIMEOUT_STYLE)
    return legend


def render_trend_graph(
    history: Sequence[float | None] | None,
    *,
    width: int | None = None,
    height: int = 4,
) -> Text:
    if not history:
        return Text("-")
    cells = trend_cells(list(history))
    if width is not None and width > 0:
        cells = cells[-width:]

    graph = Text()
    total_buckets = len(TREND_STYLES)
    for level in range(height, 0, -1):
        if graph:
            graph.append("\n")
        for _, bucket in cells:
            if bucket is None:
                graph.append(TIMEOUT_MARKER, style=TIMEOUT_STYLE)
                continue
            bucket_height = max(1, math.ceil(((bucket + 1) / total_buckets) * height))
            if bucket_height >= level:
                graph.append("█", style=TREND_STYLES[bucket])
            else:
                graph.append("·", style=DETAIL_GRAPH_EMPTY_STYLE)
    return graph

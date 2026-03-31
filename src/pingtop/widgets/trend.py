from __future__ import annotations

from collections.abc import Sequence

from rich.text import Text

from pingtop.models import trend_cells

TREND_STYLES = (
    "#d1fae5 on #14532d",
    "#bbf7d0 on #166534",
    "#ecfccb on #3f6212",
    "#fef3c7 on #92400e",
    "#fed7aa on #9a3412",
    "#fecaca on #b91c1c",
    "#ffffff on #dc2626",
    "#ffffff on #7f1d1d",
)
TIMEOUT_STYLE = "bold white on #450a0a"


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

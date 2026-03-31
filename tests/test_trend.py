from __future__ import annotations

from rich.text import Text

from pingtop.models import TIMEOUT_MARKER, TREND_BLOCKS, build_trend
from pingtop.widgets.trend import TIMEOUT_STYLE, TREND_STYLES, render_trend


def test_build_trend_uses_unicode_blocks_and_timeout_marker() -> None:
    trend = build_trend([10.0, 15.0, 30.0, None])

    assert trend.endswith(TIMEOUT_MARKER)
    assert all(block in TREND_BLOCKS for block in trend[:-1])


def test_render_trend_assigns_foreground_and_background_styles() -> None:
    trend = render_trend([10.0, 15.0, 30.0, None])

    assert isinstance(trend, Text)
    assert trend.plain.endswith(TIMEOUT_MARKER)
    assert trend.spans[-1].style == TIMEOUT_STYLE
    assert all(span.style in (*TREND_STYLES, TIMEOUT_STYLE) for span in trend.spans)


def test_render_trend_returns_dash_without_history() -> None:
    trend = render_trend([])

    assert trend.plain == "-"

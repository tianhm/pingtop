from __future__ import annotations

from rich.text import Text

from pingtop.models import TIMEOUT_MARKER, TREND_BLOCKS, build_trend
from pingtop.widgets.trend import (
    DETAIL_GRAPH_AXIS_STYLE,
    DETAIL_GRAPH_EMPTY_STYLE,
    TIMEOUT_STYLE,
    TREND_STYLES,
    render_detailed_trend_graph,
    render_trend,
    render_trend_graph,
    render_trend_legend,
)


def test_build_trend_uses_unicode_blocks_and_timeout_marker() -> None:
    trend = build_trend([10.0, 15.0, 30.0, None])

    assert trend.endswith(TIMEOUT_MARKER)
    assert all(block in TREND_BLOCKS for block in trend[:-1])


def test_render_trend_assigns_foreground_only_styles() -> None:
    trend = render_trend([10.0, 15.0, 30.0, None])

    assert isinstance(trend, Text)
    assert trend.plain.endswith(TIMEOUT_MARKER)
    assert trend.spans[-1].style == TIMEOUT_STYLE
    assert all(span.style in (*TREND_STYLES, TIMEOUT_STYLE) for span in trend.spans)
    assert all(" on " not in str(span.style) for span in trend.spans)


def test_render_trend_returns_dash_without_history() -> None:
    trend = render_trend([])

    assert trend.plain == "-"


def test_render_trend_keeps_latest_samples_when_width_is_limited() -> None:
    trend = render_trend([10.0, 12.0, 14.0, 16.0], width=2)

    assert len(trend.plain) == 2


def test_render_trend_legend_includes_all_styles() -> None:
    legend = render_trend_legend()

    assert "Trend Legend" in legend.plain
    assert "low RTT" in legend.plain
    assert "high RTT" in legend.plain
    assert TIMEOUT_MARKER in legend.plain
    assert any(span.style == TIMEOUT_STYLE for span in legend.spans)
    for style in TREND_STYLES:
        assert any(span.style == style for span in legend.spans)
    assert all(" on " not in str(span.style) for span in legend.spans)


def test_render_trend_graph_builds_multiline_chart() -> None:
    graph = render_trend_graph([10.0, 15.0, 30.0, None], width=4, height=4)

    assert isinstance(graph, Text)
    assert graph.plain.count("\n") == 3
    assert TIMEOUT_MARKER in graph.plain
    assert any(span.style == TIMEOUT_STYLE for span in graph.spans)
    assert any(span.style == DETAIL_GRAPH_EMPTY_STYLE for span in graph.spans)


def test_render_detailed_trend_graph_includes_scale_and_axis() -> None:
    graph_lines = render_detailed_trend_graph([10.0, 15.0, 30.0, None], width=4, height=4)

    assert graph_lines[0].plain.startswith("RTT Graph")
    assert any("oldest -> newest" in line.plain for line in graph_lines)
    assert any(TIMEOUT_MARKER in line.plain for line in graph_lines)
    assert any("└" in line.plain for line in graph_lines)
    assert any(
        span.style == DETAIL_GRAPH_AXIS_STYLE
        for line in graph_lines
        for span in line.spans
    )

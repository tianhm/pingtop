from __future__ import annotations

from typing import cast

import click

from pingtop.models import SessionSnapshot

MAX_ISSUES = 5


def render_summary(
    snapshot: SessionSnapshot,
    *,
    color: bool = False,
    max_issues: int = MAX_ISSUES,
) -> str:
    style = _styler(color)
    total_hosts = int(cast(int, snapshot.aggregates["total_hosts"]))
    total_sent = int(cast(int, snapshot.aggregates["total_sent"]))
    total_lost = int(cast(int, snapshot.aggregates["total_lost"]))
    error_hosts = int(cast(int, snapshot.aggregates["error_hosts"]))
    total_received = total_sent - total_lost
    lossy_hosts = sum(
        1
        for host in snapshot.hosts
        if int(cast(int, host["seq"])) > 0 and int(cast(int, host["lost"])) > 0
    )
    idle_hosts = sum(
        1
        for host in snapshot.hosts
        if int(cast(int, host["seq"])) == 0 and not host["last_error"]
    )

    status_text, status_color = _status(snapshot)
    parts = [
        style(status_text, fg=status_color, bold=True),
        f"{total_hosts} hosts",
        f"tx {total_sent}",
        f"rx {total_received}",
        f"loss {style(f'{_loss_percent(total_lost, total_sent):.1f}%', fg=_loss_color(total_lost, total_sent), bold=True)}",
    ]
    if error_hosts:
        parts.append(f"err {style(str(error_hosts), fg='red', bold=True)}")
    if lossy_hosts:
        parts.append(f"lossy {style(str(lossy_hosts), fg='yellow', bold=True)}")
    if idle_hosts:
        parts.append(f"idle {style(str(idle_hosts), fg='blue', bold=True)}")

    lines = [" | ".join(parts)]
    issue_lines = _issue_lines(snapshot, style, max_issues=max_issues)
    lines.extend(issue_lines)
    return "\n".join(lines)


def _issue_lines(
    snapshot: SessionSnapshot,
    style,
    *,
    max_issues: int,
) -> list[str]:
    issues: list[tuple[tuple[object, ...], str]] = []
    for host in snapshot.hosts:
        target = str(host["target"])
        seq = int(cast(int, host["seq"]))
        lost = int(cast(int, host["lost"]))
        error = host["last_error"]
        avg_rtt_ms = host["avg_rtt_ms"]

        if seq == 0 and error and error != "timeout":
            issues.append(
                (
                    (0, target.lower()),
                    f"{style('ERR', fg='red', bold=True)} {target} {error}",
                )
            )
            continue

        if seq == 0 or lost == 0:
            continue

        loss_percent = _loss_percent(lost, seq)
        label = "DOWN" if lost == seq else "LOSS"
        label_color = "red" if lost == seq else "yellow"
        detail = f"{loss_percent:.1f}% loss ({lost}/{seq})"
        if avg_rtt_ms is not None:
            detail += f", avg {float(cast(float, avg_rtt_ms)):.1f} ms"
        issues.append(
            (
                (1 if lost == seq else 2, -loss_percent, target.lower()),
                f"{style(label, fg=label_color, bold=True)} {target} {detail}",
            )
        )

    issues.sort(key=lambda item: item[0])
    visible = [line for _, line in issues[:max_issues]]
    if len(issues) > max_issues:
        visible.append(
            f"{style('MORE', fg='cyan', bold=True)} +{len(issues) - max_issues} more issues"
        )
    return visible


def _status(snapshot: SessionSnapshot) -> tuple[str, str]:
    has_error = any(
        int(cast(int, host["seq"])) == 0 and host["last_error"] and host["last_error"] != "timeout"
        for host in snapshot.hosts
    )
    has_down = any(
        int(cast(int, host["seq"])) > 0 and int(cast(int, host["lost"])) == int(cast(int, host["seq"]))
        for host in snapshot.hosts
    )
    has_loss = int(cast(int, snapshot.aggregates["total_lost"])) > 0
    if has_error or has_down:
        return "ERR", "red"
    if has_loss:
        return "WARN", "yellow"
    return "OK", "green"


def _loss_percent(lost: int, seq: int) -> float:
    return (lost / seq * 100) if seq else 0.0


def _loss_color(lost: int, seq: int) -> str:
    loss_percent = _loss_percent(lost, seq)
    if loss_percent >= 100.0 and seq > 0:
        return "red"
    if loss_percent > 0.0:
        return "yellow"
    return "green"


def _styler(color: bool):
    def apply(text: str, **styles: object) -> str:
        if not color:
            return text
        return click.style(text, **styles)

    return apply

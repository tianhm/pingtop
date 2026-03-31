from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path

from pingtop.models import ExportFormat, SessionSnapshot


def export_snapshot(
    snapshot: SessionSnapshot, destination: str, export_format: ExportFormat
) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    if export_format == ExportFormat.JSON:
        payload = json.dumps(_json_payload(snapshot), indent=2, sort_keys=True)
        path.write_text(payload, encoding="utf-8")
        return path
    if export_format == ExportFormat.CSV:
        _write_csv(path, snapshot)
        return path
    raise ValueError(f"Unsupported export format: {export_format}")


def _json_payload(snapshot: SessionSnapshot) -> dict[str, object]:
    return {
        "generated_at": snapshot.generated_at.isoformat(),
        "config": {
            **asdict(snapshot.config),
            "export_format": (
                snapshot.config.export_format.value
                if snapshot.config.export_format
                else None
            ),
        },
        "aggregates": snapshot.aggregates,
        "hosts": snapshot.hosts,
    }


def _write_csv(path: Path, snapshot: SessionSnapshot) -> None:
    fieldnames = [
        "id",
        "target",
        "enabled",
        "resolved_ip",
        "seq",
        "last_rtt_ms",
        "min_rtt_ms",
        "avg_rtt_ms",
        "max_rtt_ms",
        "stddev_ms",
        "lost",
        "loss_percent",
        "trend",
        "last_error",
        "state",
        "last_updated_at",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for host in snapshot.hosts:
            writer.writerow({key: host.get(key) for key in fieldnames})

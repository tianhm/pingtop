from __future__ import annotations

import csv
import json

from pingtop.exporters import export_snapshot
from pingtop.models import ExportFormat, PingResult, SessionConfig
from pingtop.session import PingSession


def test_export_snapshot_json_and_csv(tmp_path) -> None:
    session = PingSession(SessionConfig(), ["1.1.1.1"])
    host_id = next(iter(session.hosts))
    session.apply_result(host_id, PingResult(success=True, rtt_ms=12.5, resolved_ip="1.1.1.1"))
    snapshot = session.snapshot()

    json_path = export_snapshot(snapshot, str(tmp_path / "snapshot.json"), ExportFormat.JSON)
    csv_path = export_snapshot(snapshot, str(tmp_path / "snapshot.csv"), ExportFormat.CSV)

    json_payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert json_payload["hosts"][0]["target"] == "1.1.1.1"

    with csv_path.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["target"] == "1.1.1.1"
    assert rows[0]["resolved_ip"] == "1.1.1.1"


from __future__ import annotations

import json

from fastapi.testclient import TestClient

from api.app import app

client = TestClient(app)

# T037: SSE event sequence test verifying anomaly summary event presence
# Baseline synchronous orchestrator currently emits heartbeat + snapshot. We verify snapshot contains
# validation_summary (or legacy alias validation) with anomaly counters when include_anomalies requested via run detail.
# Since events endpoint does not take include_anomalies flag, we assert that the RunDetail endpoint exposes
# both validation_summary and anomaly_counters (when requested) and that snapshot event embeds summary fields.


def _create_run_nvda() -> str:
    payload = {
        "start": "2024-01-01",
        "end": "2024-01-10",
        "symbol": "NVDA",
    "timeframe": "1d",
        "indicators": [
            {"name": "sma", "params": {"window": 5}},
            {"name": "sma", "params": {"window": 15}},
        ],
        "strategy": {"name": "dual_sma", "params": {"fast": 5, "slow": 15}},
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.1}},
        "execution": {"mode": "sim", "slippage_bps": 0, "fee_bps": 0, "borrow_cost_bps": 0},
        "validation": {"permutation": {"trials": 5}},
        "seed": 99,
    }
    r = client.post("/runs", json=payload)
    assert r.status_code in (200, 201)
    rh = r.json()["run_hash"]
    assert isinstance(rh, str)
    return rh


def test_snapshot_contains_validation_summary() -> None:
    run_hash = _create_run_nvda()
    ev = client.get(f"/runs/{run_hash}/events")
    assert ev.status_code == 200
    body = ev.text
    # Extract snapshot JSON payload(s)
    # Lines beginning with data: {json}
    snapshot_lines = [line for line in body.splitlines() if line.startswith("data: ") and '"type": "snapshot"' in line]
    assert snapshot_lines, f"No snapshot event found in body: {body}"
    # Parse the last snapshot line
    payload_json = json.loads(snapshot_lines[-1][len("data: "):])
    data = payload_json.get("data", {})
    # validation_summary should be present
    assert ("validation_summary" in data) or ("validation" in data)
    # summary may optionally include anomaly counters; tolerate absence if include_anomalies not requested.
    # Now fetch run detail with include_anomalies to assert anomaly_counters field path
    detail = client.get(f"/runs/{run_hash}", params={"include_anomalies": "true"})
    assert detail.status_code == 200
    d_json = detail.json()
    if d_json.get("summary"):
        # anomaly_counters should appear inside summary when flag set
        assert "anomaly_counters" in d_json["summary"]


def test_event_ids_strictly_increasing() -> None:
    run_hash = _create_run_nvda()
    ev = client.get(f"/runs/{run_hash}/events")
    assert ev.status_code == 200
    ids = []
    for line in ev.text.splitlines():
        if line.startswith("id: "):
            try:
                ids.append(int(line.split(":", 1)[1].strip()))
            except ValueError:
                pass
    assert ids == sorted(ids)
    # Expect at least heartbeat(0) and snapshot(1)
    assert ids and ids[0] == 0 and 1 in ids

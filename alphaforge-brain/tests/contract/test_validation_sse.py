from __future__ import annotations

import json
from typing import Any

from api.app import create_app
from fastapi.testclient import TestClient


def make_client() -> TestClient:
    return TestClient(create_app())


def validation_ready_payload(seed: int = 20251011) -> dict[str, object]:
    return {
        "indicators": [
            {
                "name": "dual_sma",
                "params": {"short_window": 6, "long_window": 14},
            }
        ],
        "strategy": {
            "name": "dual_sma",
            "params": {"short_window": 6, "long_window": 14},
        },
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.15}},
        "execution": {"mode": "sim", "slippage_bps": 0.75, "fee_bps": 0.3},
        "validation": {
            "permutation": {"n": 24},
            "block_bootstrap": {"n": 12},
            "walk_forward": {"splits": 2},
        },
        "symbol": "SSE",
        "timeframe": "1m",
        "start": "2024-02-01",
        "end": "2024-02-05",
        "seed": seed,
    }


def parse_sse_events(body: str) -> list[tuple[int | None, str, dict[str, Any]]]:
    events: list[tuple[int | None, str, dict[str, Any]]] = []
    for chunk in body.strip().split("\n\n"):
        lines = [line for line in chunk.splitlines() if line.strip()]
        if not lines:
            continue
        event_id: int | None = None
        event_type = ""
        payload: dict[str, Any] = {}
        for line in lines:
            if line.startswith("id:"):
                try:
                    event_id = int(line.split(":", 1)[1].strip())
                except ValueError:
                    event_id = None
            elif line.startswith("event:"):
                event_type = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data_str = line.split(":", 1)[1].strip()
                payload = json.loads(data_str)
        events.append((event_id, event_type, payload))
    return events


def test_validation_stream_includes_snapshot_with_validation_metadata() -> None:
    client = make_client()
    creation = client.post("/runs", json=validation_ready_payload())
    assert creation.status_code == 200, creation.text
    run_hash = creation.json()["run_hash"]

    response = client.get(f"/runs/{run_hash}/events")
    assert response.status_code == 200, response.text
    assert response.headers.get("content-type", "").startswith("text/event-stream")

    correlation_id = response.headers.get("x-correlation-id")
    assert correlation_id, "SSE response must include correlation id header"

    events = parse_sse_events(response.text)
    assert len(events) >= 2, "expected at least heartbeat and snapshot events"

    first_id, first_type, first_payload = events[0]
    assert first_id == 0
    assert first_type == "heartbeat"
    assert first_payload.get("type") == "heartbeat"
    heartbeat_data = first_payload.get("data", {})
    assert heartbeat_data.get("status") == "COMPLETE"

    snapshot_id, snapshot_type, snapshot_payload = events[1]
    assert snapshot_id == 1
    assert snapshot_type == "snapshot"
    assert snapshot_payload.get("type") == "snapshot"

    snapshot_data = snapshot_payload.get("data", {})
    assert snapshot_data.get("run_hash") == run_hash

    validation = snapshot_data.get("validation")
    assert isinstance(validation, dict)
    for key in ["permutation_p", "block_bootstrap_p", "walk_forward_folds"]:
        assert key in validation

    validation_summary = snapshot_data.get("validation_summary")
    assert isinstance(validation_summary, dict)
    assert validation_summary == validation

    p_values = snapshot_data.get("p_values")
    assert isinstance(p_values, dict)
    assert set(p_values) >= {"perm", "bb"}

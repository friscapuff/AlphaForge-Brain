from __future__ import annotations

from api.app import create_app
from fastapi.testclient import TestClient


def test_sse_long_lived_stream_receives_snapshot_and_completes():
    app = create_app()
    client = TestClient(app)
    payload = {
        "indicators": [],
        "strategy": {"name": "dual_sma", "params": {"fast": 5, "slow": 20}},
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.1}},
        "execution": {"mode": "sim"},
        "validation": {},
        "symbol": "NVDA",
        "timeframe": "1d",
        "start": "2024-01-01",
        "end": "2024-02-01",
        "seed": 42,
    }
    r = client.post("/runs", json=payload)
    run_hash = r.json()["run_hash"]
    # Long-lived stream; since orchestrator finished synchronously buffer should have stage + snapshot + completed
    resp = client.get(f"/runs/{run_hash}/events/stream")
    assert resp.status_code == 200
    body = resp.content.decode()
    # Expect at least one snapshot and a completed event
    assert "snapshot" in body
    assert "completed" in body or "COMPLETE" in body
    # No infinite loop (response finite)
    assert len(body) < 10000, body[:1000]

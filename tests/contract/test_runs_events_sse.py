from __future__ import annotations

from fastapi.testclient import TestClient

from api.app import app

client = TestClient(app)


def _create_run() -> str:
    payload = {
        "start": "2024-01-01",
        "end": "2024-01-02",
        "symbol": "TEST",
        "timeframe": "1m",
        "indicators": [{"name": "sma", "params": {"window": 5}}],
        "strategy": {"name": "dual_sma", "params": {"fast": 5, "slow": 10}},
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.1}},
        "execution": {"slippage_bps": 0, "fee_bps": 0},
        "seed": 999,
    }
    r = client.post("/runs", json=payload)
    assert r.status_code == 200
    return r.json()["run_hash"]


def test_runs_events_sse_contract() -> None:  # T009
    run_hash = _create_run()
    # First fetch should contain heartbeat and snapshot events
    resp = client.get(f"/runs/{run_hash}/events")
    assert resp.status_code == 200
    body = resp.text
    assert "event: heartbeat" in body
    assert "event: snapshot" in body
    # Subsequent fetch with Last-Event-ID=1 should yield empty (no new events)
    resp2 = client.get(f"/runs/{run_hash}/events", headers={"Last-Event-ID": "1"})
    assert resp2.status_code == 200
    # No new snapshot lines expected
    assert "event: snapshot" not in resp2.text

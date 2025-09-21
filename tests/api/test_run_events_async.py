from __future__ import annotations

from _pytest.monkeypatch import MonkeyPatch
from fastapi.testclient import TestClient

from api.app import app


def test_run_events_async_progress(monkeypatch: MonkeyPatch) -> None:
    client = TestClient(app)
    payload = {
        "start": "2024-01-01",
        "end": "2024-01-02",
        "symbol": "ASYNC",
        "timeframe": "1m",
        "indicators": [
            {"name": "sma", "params": {"window": 5}},
            {"name": "sma", "params": {"window": 15}},
        ],
        "strategy": {"name": "dual_sma", "params": {"fast": 5, "slow": 15}},
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.1}},
        "execution": {"mode": "sim", "slippage_bps": 0, "fee_bps": 0, "borrow_cost_bps": 0},
        "validation": {"permutation": {"trials": 3}},
        "seed": 42,
    }
    r = client.post("/runs", json=payload)
    assert r.status_code == 200
    run_hash = r.json()["run_hash"]

    # Stream events (since our async orchestration completes quickly we get all immediately)
    ev = client.get(f"/runs/{run_hash}/events")
    assert ev.status_code == 200
    body = ev.text
    # Expect snapshot and run_hash present
    assert "event: snapshot" in body or "event: stage" in body
    assert run_hash in body

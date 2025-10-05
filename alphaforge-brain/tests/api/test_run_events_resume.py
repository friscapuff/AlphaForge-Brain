from __future__ import annotations

from api.app import app
from fastapi.testclient import TestClient

client = TestClient(app)


def _create_run() -> str:
    payload = {
        "start": "2024-01-01",
        "end": "2024-01-10",
        "symbol": "TEST",
        "timeframe": "1m",
        "indicators": [
            {"name": "sma", "params": {"window": 5}},
            {"name": "sma", "params": {"window": 15}},
        ],
        "strategy": {"name": "dual_sma", "params": {"fast": 5, "slow": 15}},
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.1}},
        "execution": {
            "mode": "sim",
            "slippage_bps": 0,
            "fee_bps": 0,
            "borrow_cost_bps": 0,
        },
        "validation": {"permutation": {"trials": 5}},
        "seed": 123,
    }
    r = client.post("/runs", json=payload)
    assert r.status_code in (200, 201)
    run_hash = r.json().get("run_hash")
    assert isinstance(run_hash, str)
    return run_hash


def test_resume_full_then_empty() -> None:
    run_hash = _create_run()
    # First fetch: should get heartbeat (id 0) and snapshot (id 1)
    r1 = client.get(f"/runs/{run_hash}/events")
    assert r1.status_code == 200
    body1 = r1.text
    assert "id: 0" in body1 and "id: 1" in body1

    # Second fetch with Last-Event-ID=1 should yield nothing (already up to date)
    r2 = client.get(f"/runs/{run_hash}/events", headers={"Last-Event-ID": "1"})
    assert r2.status_code == 200
    body2 = r2.text.strip()
    assert body2 == ""  # no new events

    # Fetch with Last-Event-ID=-1 (invalid) -> treat as None and resend both
    r3 = client.get(f"/runs/{run_hash}/events", headers={"Last-Event-ID": "-1"})
    assert r3.status_code == 200
    body3 = r3.text
    assert "id: 0" in body3 and "id: 1" in body3

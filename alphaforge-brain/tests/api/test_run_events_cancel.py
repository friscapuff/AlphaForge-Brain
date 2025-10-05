from __future__ import annotations

from api.app import app
from fastapi.testclient import TestClient

client = TestClient(app)


def _create_run() -> str:
    payload = {
        "start": "2024-01-01",
        "end": "2024-01-05",
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
        "validation": {"permutation": {"trials": 3}},
        "seed": 42,
    }
    r = client.post("/runs", json=payload)
    assert r.status_code in (200, 201)
    run_hash = r.json().get("run_hash")
    assert isinstance(run_hash, str)
    return run_hash


def test_cancel_emits_event() -> None:
    run_hash = _create_run()
    # Prime buffer (heartbeat + snapshot)
    initial = client.get(f"/runs/{run_hash}/events")
    assert initial.status_code == 200
    assert "snapshot" in initial.text

    # Cancel the run (even though already complete synchronously) - should still append cancelled event
    c = client.post(f"/runs/{run_hash}/cancel")
    assert c.status_code == 200
    assert c.json()["status"] == "CANCELLED"

    # Fetch events since id=1 (expect only cancelled)
    ev = client.get(f"/runs/{run_hash}/events", headers={"Last-Event-ID": "1"})
    assert ev.status_code == 200
    body = ev.text
    # We expect at most one new event labelled cancelled
    assert "event: cancelled" in body
    assert 'status": "CANCELLED"' in body

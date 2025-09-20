from fastapi.testclient import TestClient

from api.app import app

client = TestClient(app)


def test_run_events_stream_basic():
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
        "execution": {"mode": "sim", "slippage_bps": 0, "fee_bps": 0, "borrow_cost_bps": 0},
        "validation": {"permutation": {"trials": 10}, "block_bootstrap": {"trials": 5, "block_size": 5}, "monte_carlo": {"trials": 5, "slippage_bps": 10}},
        "seed": 123,
    }
    r = client.post("/runs", json=payload)
    assert r.status_code == 200
    run_hash = r.json()["run_hash"]

    ev = client.get(f"/runs/{run_hash}/events")
    assert ev.status_code == 200
    assert ev.headers.get("content-type", "").startswith("text/event-stream")
    body = ev.text
    # Expect heartbeat and snapshot events
    assert "event: heartbeat" in body
    assert "event: snapshot" in body
    assert run_hash in body

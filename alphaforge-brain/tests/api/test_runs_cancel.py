from __future__ import annotations

from api.app import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_run_cancel_endpoint() -> None:
    # create a run
    payload = {
        "indicators": [{"name": "dual_sma", "params": {"fast": 5, "slow": 20}}],
        "strategy": {
            "name": "dual_sma",
            "params": {"short_window": 5, "long_window": 20},
        },
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.1}},
        "execution": {"slippage_bps": 0, "fee_bps": 0},
        "validation": {
            "permutation": {"n": 10},
            "block_bootstrap": {"n_iter": 10},
            "monte_carlo": {"n_iter": 10},
            "walk_forward": {"n_folds": 2},
        },
        "symbol": "TEST",
        "timeframe": "1m",
        "start": "2024-01-01",
        "end": "2024-01-05",
        "seed": 42,
    }
    r = client.post("/runs", json=payload)
    assert r.status_code == 200
    run_hash = r.json()["run_hash"]

    # cancel
    c = client.post(f"/runs/{run_hash}/cancel")
    assert c.status_code == 200
    data = c.json()
    assert data["run_hash"] == run_hash
    assert data["status"] in {"CANCELLED", "COMPLETE"}

    # second cancel idempotent
    c2 = client.post(f"/runs/{run_hash}/cancel")
    assert c2.status_code == 200
    data2 = c2.json()
    assert data2["status"] in {"CANCELLED", "COMPLETE"}

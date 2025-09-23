from __future__ import annotations

from fastapi.testclient import TestClient

from api.app import app

client = TestClient(app)


def test_post_runs_contract_shape() -> None:  # T007
    payload = {
        "start": "2024-01-01",
        "end": "2024-01-02",
        "symbol": "TEST",
        "timeframe": "1m",
        "indicators": [{"name": "sma", "params": {"window": 5}}],
        "strategy": {"name": "dual_sma", "params": {"fast": 5, "slow": 10}},
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.1}},
        "execution": {"slippage_bps": 0, "fee_bps": 0},
        "seed": 55,
    }
    r = client.post("/runs", json=payload)
    assert r.status_code == 200
    body = r.json()
    for key in ["run_id", "run_hash", "status", "created_at", "created"]:
        assert key in body
    assert body["status"] == "SUCCEEDED"
    assert isinstance(body["created"], bool)

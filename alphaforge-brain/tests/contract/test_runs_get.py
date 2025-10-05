from __future__ import annotations

from api.app import app
from fastapi.testclient import TestClient

client = TestClient(app)


def _create_run(symbol: str = "LIST", seed: int = 77) -> str:
    payload = {
        "start": "2024-01-01",
        "end": "2024-01-02",
        "symbol": symbol,
        "timeframe": "1m",
        "indicators": [{"name": "sma", "params": {"window": 5}}],
        "strategy": {"name": "dual_sma", "params": {"fast": 5, "slow": 10}},
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.1}},
        "execution": {"slippage_bps": 0, "fee_bps": 0},
        "seed": seed,
    }
    r = client.post("/runs", json=payload)
    assert r.status_code == 200
    return r.json()["run_hash"]


def test_get_runs_contract_shape() -> None:  # T008
    h1 = _create_run(symbol="TEST", seed=1)
    h2 = _create_run(symbol="TEST", seed=2)
    resp = client.get("/runs")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    hashes = {item["run_hash"] for item in data["items"]}
    assert {h1, h2}.issubset(hashes)
    # items should be list of dicts with run_hash key
    for item in data["items"]:
        assert "run_hash" in item

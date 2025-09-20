from fastapi.testclient import TestClient

from api.app import app

client = TestClient(app)


def create_run():
    payload = {
        "indicators": [
            {"name": "dual_sma", "params": {"fast": 5, "slow": 20}}
        ],
        "strategy": {"name": "dual_sma", "params": {"short_window": 5, "long_window": 20}},
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.1}},
        "execution": {"slippage_bps": 0, "fee_bps": 0},
        "validation": {"permutation": {"n": 5}, "block_bootstrap": {"n_iter": 5}, "monte_carlo": {"n_iter": 5}, "walk_forward": {"n_folds": 2}},
        "symbol": "TEST",
        "timeframe": "1m",
        "start": "2024-01-01",
        "end": "2024-01-10",
        "seed": 123,
    }
    r = client.post("/runs", json=payload)
    assert r.status_code == 200
    return r.json()["run_hash"]


def test_artifacts_listing_and_fetch():
    run_hash = create_run()
    # list artifacts
    r = client.get(f"/runs/{run_hash}/artifacts")
    assert r.status_code == 200
    files = r.json()["files"]
    assert any(f.get("name") == "summary.json" for f in files)
    # fetch one
    r2 = client.get(f"/runs/{run_hash}/artifacts/summary.json")
    assert r2.status_code == 200
    assert r2.headers["content-type"].startswith("application/json")
    assert "trade_count" in r2.json()

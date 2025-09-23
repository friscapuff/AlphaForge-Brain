from __future__ import annotations

from fastapi.testclient import TestClient

from api.app import create_app


def test_anomalies_snapshot() -> None:  # T018
    app = create_app()
    client = TestClient(app)
    payload = {
        "start": "2024-01-01",
        "end": "2024-01-03",
        "symbol": "TEST",
        "timeframe": "1m",
        "indicators": [{"name": "sma", "params": {"window": 5}}],
        "strategy": {"name": "dual_sma", "params": {"fast": 5, "slow": 10}},
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.1}},
        "execution": {"slippage_bps": 0, "fee_bps": 0},
        "seed": 101,
    }
    r = client.post("/runs", json=payload)
    assert r.status_code == 200
    run_hash = r.json()["run_hash"]
    # fetch anomalies via include_anomalies flag
    detail = client.get(f"/runs/{run_hash}?include_anomalies=true").json()
    summary = detail.get("summary", {})
    # anomaly_counters may be synthesized or empty; assert key exists and is a dict
    assert "anomaly_counters" in summary
    assert isinstance(summary["anomaly_counters"], dict)

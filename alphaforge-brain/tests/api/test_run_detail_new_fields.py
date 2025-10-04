from __future__ import annotations

from api.app import app
from fastapi.testclient import TestClient

client = TestClient(app)


def _payload() -> dict[str, object]:
    return {
        "start": "2024-01-01",
        "end": "2024-01-02",
        # Use a symbol that triggers synthetic dataset generation in orchestrator fallback
        "symbol": "TEST",
        "timeframe": "1m",
        "indicators": [
            {"name": "sma", "params": {"window": 5}},
        ],
        "strategy": {"name": "dual_sma", "params": {"fast": 5, "slow": 15}},
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.1}},
        "execution": {"mode": "sim", "slippage_bps": 0, "fee_bps": 0},
        "seed": 111,
    }


def test_run_detail_includes_new_dataset_fields_and_alias() -> None:
    p = _payload()
    r = client.post("/runs", json=p)
    assert r.status_code == 200
    run_hash = r.json()["run_hash"]

    # Fetch without anomalies
    detail = client.get(f"/runs/{run_hash}").json()
    assert set(
        ["data_hash", "calendar_id", "validation_summary", "validation"]
    ).issubset(detail.keys())
    # validation alias should mirror validation_summary exactly
    assert detail.get("validation_summary") == detail.get("validation")

    # When include_anomalies=true summary should contain anomaly_counters key (even if empty dict)
    detail_with = client.get(f"/runs/{run_hash}?include_anomalies=true").json()
    summary_obj = detail_with.get("summary", {})
    assert (
        "anomaly_counters" in summary_obj
    ), "anomaly_counters missing when include_anomalies=true"

from __future__ import annotations

from api.app import create_app
from fastapi.testclient import TestClient


def _make_run(client: TestClient, seed: int) -> str:
    payload = {
        "indicators": [],
        "strategy": {"name": "dual_sma", "params": {"fast": 5, "slow": 20}},
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.1}},
        "execution": {"mode": "sim"},
        "validation": {},
        "symbol": "NVDA",
        "timeframe": "1d",
        "start": "2024-01-01",
        "end": "2024-02-01",
        "seed": seed,
    }
    r = client.post("/runs", json=payload)
    assert r.status_code == 200
    return r.json()["run_hash"]


def test_retention_metrics_counts():
    app = create_app()
    client = TestClient(app)
    runs = [_make_run(client, 5000 + i) for i in range(5)]
    # Aggressive demotion configuration
    client.post(
        "/settings/retention",
        json={"keep_last": 1, "top_k_per_strategy": 0, "max_full_bytes": 10_000_000},
    )
    client.post("/runs/retention/apply")
    # Metrics endpoint should reflect exactly 1 full and 4 manifest-only runs
    m = client.get("/retention/metrics")
    assert m.status_code == 200, m.text
    data = m.json()
    assert data["counts"]["full"] == 1
    assert data["counts"]["manifest-only"] >= 4  # pinned/top_k could adjust in future
    assert data["counts"]["total"] == 5
    # New fields assertions
    assert "max_full_bytes" in data
    assert "bytes" in data
    bytes_map = data["bytes"]
    for k, v in bytes_map.items():
        assert (
            isinstance(v, int) and v >= 0
        ), f"byte count for {k} should be non-negative int"
    # total_bytes must equal sum of component categories (exclude total_bytes itself)
    component_sum = sum(
        bytes_map[k]
        for k in ("full", "pinned", "top_k", "manifest-only")
        if k in bytes_map
    )
    assert bytes_map.get("total_bytes") == component_sum
    # budget_remaining logic: must be None if max_full_bytes is None else non-negative
    if data.get("max_full_bytes") is None:
        assert data.get("budget_remaining") is None
    else:
        assert isinstance(data.get("budget_remaining"), int)
        assert data["budget_remaining"] >= 0

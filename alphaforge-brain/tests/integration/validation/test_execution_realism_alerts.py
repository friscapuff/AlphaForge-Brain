from __future__ import annotations

import pytest
from api.app import create_app
from fastapi.testclient import TestClient

xfail_realism = pytest.mark.xfail(
    reason="Execution realism validation not implemented",
    strict=False,
)


def _client() -> TestClient:
    return TestClient(create_app())


@xfail_realism
@pytest.mark.integration
def test_execution_realism_reports_cost_impact_capacity_guidance() -> None:
    client = _client()
    payload = {
        "indicators": [
            {"name": "dual_sma", "params": {"short_window": 8, "long_window": 20}}
        ],
        "strategy": {
            "name": "dual_sma",
            "params": {"short_window": 8, "long_window": 20},
        },
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.3}},
        "execution": {"mode": "sim", "slippage_bps": 0.4, "fee_bps": 0.2},
        "validation": {
            "realism": {
                "capacity_ratio_threshold": 0.8,
                "cost_limit_bps": 500,
            }
        },
        "symbol": "SSE",
        "timeframe": "1m",
        "start": "2024-05-01",
        "end": "2024-05-05",
        "seed": 1234,
    }

    response = client.post("/runs", json=payload)
    assert response.status_code == 200
    run_hash = response.json()["run_hash"]

    detail = client.get(f"/runs/{run_hash}")
    assert detail.status_code == 200
    body = detail.json()

    realism = body["validation"]["execution_realism"]
    assert realism["status"] in {"pass", "caution", "fail"}
    assert realism["transaction_cost_bps"] >= 0
    assert realism["impact_bps"] >= 0
    assert 0 <= realism["capacity_ratio"] <= 1
    assert isinstance(realism["warnings"], list)
    assert realism["guidance"]["remediation"]

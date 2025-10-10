from __future__ import annotations

import pytest
from api.app import create_app
from fastapi.testclient import TestClient

xfail_bias = pytest.mark.xfail(
    reason="Sharpe bias adjustment integration not implemented",
    strict=False,
)


def _client() -> TestClient:
    return TestClient(create_app())


@xfail_bias
@pytest.mark.integration
def test_bias_adjustments_surface_dsr_psr_and_trials() -> None:
    client = _client()
    payload = {
        "indicators": [
            {"name": "dual_sma", "params": {"short_window": 4, "long_window": 16}}
        ],
        "strategy": {
            "name": "dual_sma",
            "params": {"short_window": 4, "long_window": 16},
        },
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.25}},
        "execution": {"mode": "sim", "slippage_bps": 0.2, "fee_bps": 0.1},
        "validation": {
            "permutation": {"count": 400},
            "bias_adjustments": {"assumed_trials": 120, "benchmark_sharpe": 0.5},
        },
        "symbol": "SSE",
        "timeframe": "1m",
        "start": "2024-03-01",
        "end": "2024-03-05",
        "seed": 2718,
    }

    creation = client.post("/runs", json=payload)
    assert creation.status_code == 200
    run_hash = creation.json()["run_hash"]

    detail = client.get(f"/runs/{run_hash}")
    assert detail.status_code == 200
    body = detail.json()

    adjustments = body["validation"]["bias_adjustments"]
    assert pytest.approx(adjustments["observed_sharpe"], rel=1e-3) > 0
    assert (
        pytest.approx(adjustments["deflated_sharpe"], rel=1e-3)
        < adjustments["observed_sharpe"]
    )
    assert 0 <= adjustments["probabilistic_sharpe"] <= 1
    assert adjustments["assumed_trials"] == 120
    assert adjustments["benchmark_sharpe"] == 0.5
    assert adjustments["status"] in {"pass", "caution", "fail"}

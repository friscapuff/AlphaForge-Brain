from __future__ import annotations

import pytest
from api.app import create_app
from fastapi.testclient import TestClient

xfail_cv = pytest.mark.xfail(
    reason="Cross-validation leakage controls not implemented",
    strict=False,
)


def _client() -> TestClient:
    return TestClient(create_app())


@xfail_cv
@pytest.mark.integration
def test_cross_validation_reports_leakage_scores_and_bias_flags() -> None:
    client = _client()
    payload = {
        "indicators": [
            {"name": "dual_sma", "params": {"short_window": 3, "long_window": 9}}
        ],
        "strategy": {
            "name": "dual_sma",
            "params": {"short_window": 3, "long_window": 9},
        },
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.15}},
        "execution": {"mode": "sim", "slippage_bps": 0.3, "fee_bps": 0.2},
        "validation": {
            "cross_validation": {
                "mode": "cpcv",
                "folds": 6,
                "purge_span_days": 45,
            }
        },
        "symbol": "SSE",
        "timeframe": "1m",
        "start": "2024-04-01",
        "end": "2024-04-06",
        "seed": 1618,
    }
    res = client.post("/runs", json=payload)
    assert res.status_code == 200
    run_hash = res.json()["run_hash"]

    detail = client.get(f"/runs/{run_hash}")
    assert detail.status_code == 200
    body = detail.json()

    cross_validation = body["validation"]["cross_validation"]
    assert cross_validation["mode"] == "cpcv"
    assert cross_validation["purge_span_days"] == 45
    assert cross_validation["leakage_score"] < 0.1
    assert cross_validation["bias_flag"] in {"pass", "caution", "fail"}

    folds = cross_validation["folds"]
    assert len(folds) == 6
    for fold in folds:
        assert fold["train_start"] < fold["train_end"]
        assert fold["test_start"] < fold["test_end"]
        assert fold["performance"]["sharpe"] is not None

from __future__ import annotations

from api.app import create_app
from fastapi.testclient import TestClient


def make_client() -> TestClient:
    return TestClient(create_app())


def validation_ready_payload(seed: int = 20251010) -> dict[str, object]:
    return {
        "indicators": [
            {
                "name": "dual_sma",
                "params": {"short_window": 5, "long_window": 12},
            }
        ],
        "strategy": {
            "name": "dual_sma",
            "params": {"short_window": 5, "long_window": 12},
        },
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.1}},
        "execution": {"mode": "sim", "slippage_bps": 0.5, "fee_bps": 0.25},
        "validation": {
            "permutation": {"n": 32},
            "block_bootstrap": {"n": 16},
            "walk_forward": {"splits": 3},
        },
        "symbol": "SSE",
        "timeframe": "1m",
        "start": "2024-01-01",
        "end": "2024-01-05",
        "seed": seed,
    }


def test_run_detail_includes_validation_contract_fields() -> None:
    client = make_client()
    response = client.post("/runs", json=validation_ready_payload())
    assert response.status_code == 200, response.text
    run_hash = response.json()["run_hash"]

    detail = client.get(f"/runs/{run_hash}")
    assert detail.status_code == 200, detail.text
    payload = detail.json()

    assert "validation" in payload, "validation payload missing from run detail"
    validation = payload["validation"]
    assert isinstance(validation, dict)
    expected_keys = {
        "permutation_p",
        "block_bootstrap_p",
        "block_bootstrap_ci_width",
        "monte_carlo_p",
        "walk_forward_folds",
        "block_bootstrap_gate_passed",
        "anomaly_counters",
    }
    assert expected_keys <= validation.keys()
    assert validation["walk_forward_folds"] >= 1

    anomaly_counters = validation["anomaly_counters"]
    assert isinstance(anomaly_counters, dict)
    for key in [
        "duplicates_dropped",
        "rows_dropped_missing",
        "zero_volume_rows",
        "future_rows_dropped",
        "unexpected_gaps",
        "expected_closures",
    ]:
        assert key in anomaly_counters

    validation_summary = payload.get("validation_summary")
    assert validation_summary == validation

    artifact_names = {artifact["name"] for artifact in payload.get("artifacts", [])}
    assert "validation_detail.json" in artifact_names

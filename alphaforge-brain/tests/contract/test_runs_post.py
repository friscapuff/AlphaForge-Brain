from __future__ import annotations

from api.app import app
from fastapi.testclient import TestClient

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


def test_post_runs_contract_sweep_shape() -> None:
    payload = {
        "start": "2024-01-01",
        "end": "2024-01-02",
        "symbol": "TEST",
        "timeframe": "1m",
        "strategy": {
            "name": "dual_sma",
            "parameters": {
                "fast": {"mode": "list", "values": [5, 8]},
                "slow": {
                    "mode": "range",
                    "range": {"start": 30, "stop": 61, "step": 15},
                },
            },
        },
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.1}},
        "execution": {"slippage_bps": 0, "fee_bps": 0},
    }

    response = client.post("/runs", json=payload)
    assert response.status_code == 202
    body = response.json()

    expected_keys = {
        "run_id",
        "run_hash",
        "status",
        "created_at",
        "created",
        "sweep_id",
        "optimization_mode",
        "combination_count",
        "normalized_parameters",
    }
    assert expected_keys.issubset(body.keys())
    assert body["status"] == "ACCEPTED"
    assert body["optimization_mode"] == "sweep"
    assert body["combination_count"] == 6
    assert body["run_id"] == body["sweep_id"]
    assert body["created"] is True
    # Normalized parameters preserve list/range declaration for manifest evidence
    parameters = body["normalized_parameters"]
    assert parameters["fast"]["values"] == [5, 8]
    assert parameters["slow"]["range"] == {"start": 30, "stop": 61, "step": 15}

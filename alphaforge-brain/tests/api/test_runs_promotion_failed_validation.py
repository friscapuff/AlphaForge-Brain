"""API promotion gating tests (US1/T007)."""

from __future__ import annotations

from api.app import app
from fastapi.testclient import TestClient
from models.run_validation_status import RunValidationStatus

client = TestClient(app)


def _submit_run() -> str:
    payload = {
        "indicators": [{"name": "dual_sma", "params": {"fast": 5, "slow": 20}}],
        "strategy": {
            "name": "dual_sma",
            "params": {"short_window": 5, "long_window": 20},
        },
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.1}},
        "execution": {"slippage_bps": 0, "fee_bps": 0},
        "validation": {
            "permutation": {"n": 10},
            "block_bootstrap": {"n_iter": 10},
            "monte_carlo": {"n_iter": 10},
            "walk_forward": {"n_folds": 2},
        },
        "symbol": "TEST",
        "timeframe": "1m",
        "start": "2024-01-01",
        "end": "2024-01-05",
        "seed": 42,
    }
    response = client.post("/runs", json=payload)
    assert response.status_code == 200
    data = response.json()
    return data["run_hash"]


def test_promotion_rejected_for_failed_validation() -> None:
    run_hash = _submit_run()

    registry = app.state.registry
    record = registry.get(run_hash)
    assert record is not None
    record["validation_status"] = RunValidationStatus.FAILED_VALIDATION.value
    registry.set(run_hash, record)

    resp = client.post(
        f"/runs/{run_hash}/promotion",
        json={"waiver_id": "gov-waiver-001"},
    )

    assert resp.status_code == 409
    payload = resp.json()
    assert payload["error_code"] == "FAILED_VALIDATION"
    assert "FAILED_VALIDATION" in payload["message"]

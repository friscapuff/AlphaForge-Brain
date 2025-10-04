from __future__ import annotations

import pytest
from api.app import app
from fastapi.testclient import TestClient

client = TestClient(app)

CORE_KEYS = {
    "run_id",
    "status",
    "equity_curve",
    "metrics",
    "trades_summary",
    "walk_forward",
    "seed",
    "strategy_hash",
    # T015 additions
    "validation_caution",
    "optimization_mode",
}


@pytest.mark.unit
@pytest.mark.feature008
def test_t099_backtest_result_core_keys_present_snapshot():
    """T099: Backtest result schema snapshot (additive-safe).

    Ensures new fields from T015 persist and baseline core keys remain. Allows
    additional future keys (test is subset-based). Also verifies advanced.warnings
    injection shape when advanced is provided.
    """
    payload = {
        "symbol": "SNAPTEST",
        "date_range": {"start": "2024-10-01", "end": "2024-10-03"},
        "strategy": {"name": "dual_sma"},
        "risk": {"initial_equity": 12000},
        "advanced": {"regime_flags": ["bull"]},
    }
    create = client.post("/api/v1/backtests", json=payload)
    assert create.status_code == 202, create.text
    run_id = create.json()["run_id"]
    resp = client.get(f"/api/v1/backtests/{run_id}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    missing = CORE_KEYS - set(body.keys())
    assert not missing, f"Missing expected keys: {missing}"
    # Type checks / shapes
    assert isinstance(body["equity_curve"], list)
    assert isinstance(body["metrics"], dict)
    assert isinstance(body["trades_summary"], dict)
    assert isinstance(body.get("walk_forward"), dict)
    # New fields default None
    assert body.get("validation_caution") is None
    assert body.get("optimization_mode") is None
    adv = body.get("advanced")
    assert isinstance(adv, dict) and isinstance(adv.get("warnings"), list)
    assert adv.get("warnings") == []

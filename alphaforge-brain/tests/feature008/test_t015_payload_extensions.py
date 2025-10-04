from __future__ import annotations

import pytest
from api.app import app
from fastapi.testclient import TestClient

client = TestClient(app)


@pytest.mark.unit
@pytest.mark.feature008
def test_t015_backtest_result_includes_new_fields_defaults():
    """T015: Ensure additive payload extension fields exist with safe defaults.

    Contract expectations (Phase 1):
      - validation_caution present and is None (not yet computed)
      - optimization_mode present and is None
      - advanced.warnings present (empty list) when advanced dict provided in submission
    """
    payload = {
        "symbol": "T015SYM",
        "date_range": {"start": "2024-09-01", "end": "2024-09-05"},
        "strategy": {"name": "dual_sma"},
        "risk": {"initial_equity": 10000},
        "advanced": {"regime_flags": ["bull"]},  # triggers advanced echo
    }
    r = client.post("/api/v1/backtests", json=payload)
    assert r.status_code == 202, r.text
    run_id = r.json()["run_id"]
    res = client.get(f"/api/v1/backtests/{run_id}")
    assert res.status_code == 200, res.text
    body = res.json()
    # Top-level new fields
    assert "validation_caution" in body, "validation_caution missing"
    assert body["validation_caution"] is None
    assert "optimization_mode" in body, "optimization_mode missing"
    assert body["optimization_mode"] is None
    # Nested warnings list (advanced present)
    adv = body.get("advanced")
    assert isinstance(adv, dict) and "warnings" in adv, "advanced.warnings missing"
    assert adv["warnings"] == [], "warnings not empty list default"


@pytest.mark.unit
@pytest.mark.feature008
def test_t015_backtest_result_without_advanced_has_fields():
    """T015: Even without advanced submission new top-level keys appear."""
    payload = {
        "symbol": "T015NOADV",
        "date_range": {"start": "2024-09-10", "end": "2024-09-12"},
        "strategy": {"name": "dual_sma"},
        "risk": {"initial_equity": 5000},
    }
    r = client.post("/api/v1/backtests", json=payload)
    assert r.status_code == 202
    run_id = r.json()["run_id"]
    res = client.get(f"/api/v1/backtests/{run_id}")
    body = res.json()
    assert body.get("validation_caution") is None
    assert body.get("optimization_mode") is None
    # advanced absent -> ok
    assert body.get("advanced") is None

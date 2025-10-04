from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from api.app import app
from fastapi.testclient import TestClient
from jsonschema import (
    validate as _jsonschema_validate,
)  # already installed (jsonschema>=4)

"""Phase 3.3B Backend Test-First Tasks (T060-T066)

All tests except T061 are marked xfail until the corresponding endpoints / models
are implemented (T067+). This establishes the contract & desired behavior up front
per Test-First principle (TF, DET).

Endpoints planned (not yet implemented unless noted):
 - GET /api/v1/market/candles (T067)
 - POST /api/v1/backtests (T068)
 - GET /api/v1/backtests/{run_id} (T069 full payload; minimal status exists via /backtests/{run_id})
 - POST /api/v1/backtests/{run_id}/montecarlo (T070)
 - GET /api/v1/backtests/{run_id}/walkforward (T072 if separate)

Current interim endpoints present:
 - POST /backtest/run (legacy path used for T061 validation test)
 - GET /backtests/{run_id} (status-only minimal adapter)
"""

client = TestClient(app)


# Resolve repository root relative to this file location to avoid CWD issues when tests run from another working directory (e.g. mind project)
SCHEMA_DIR = (
    Path(__file__).resolve().parents[3] / "specs" / "006-begin-work-on" / "contracts"
)


def _load_schema(name: str) -> dict[str, Any]:
    path = SCHEMA_DIR / name
    assert path.exists(), f"Schema file missing: {path}"
    import json

    return json.loads(path.read_text("utf-8"))


# T060 ---------------------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.feature006
def test_t060_candles_schema_parity() -> None:
    """T060: API schema parity test for candles payload (active)."""
    schema = _load_schema("chart-candles.v1.schema.json")
    # Use narrow time window; fallback empty array still valid per schema (candles optional length)
    import datetime as _dt

    now = _dt.datetime.utcnow().replace(microsecond=0)
    earlier = now - _dt.timedelta(hours=1)
    resp = client.get(
        "/api/v1/market/candles",
        params={
            "symbol": "TESTSYM",
            "interval": "1h",
            "from_": earlier.isoformat() + "Z",
            "to": now.isoformat() + "Z",
            "limit": 50,
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    # Validate full schema
    _jsonschema_validate(instance=data, schema=schema)
    # Additional invariants
    assert data["symbol"].upper() == "TESTSYM".upper()
    assert data["interval"] == "1h"
    assert "candles" in data


# T068 (partially activated) ----------------------------------------------------
@pytest.mark.integration
@pytest.mark.feature006
def test_t068_backtest_submission_endpoint_basic() -> None:
    """T068: Backtest submission versioned endpoint returns run_id and 202.

    Validates new POST /api/v1/backtests additive endpoint does not break legacy.
    """
    payload = {
        # Use symbol TEST to leverage orchestrator synthetic dataset path until real dataset registration for BTCUSD added (future task)
        "symbol": "TEST",
        "date_range": {"start": "2024-01-01", "end": "2024-01-10"},
        "strategy": {"name": "dual_sma", "params": {"fast": 5, "slow": 10}},
        "risk": {
            "initial_equity": 10000,
            "position_sizing": "fixed_fraction",
            "fraction": 0.02,
        },
        "validation": {},
        "seed": 123,
    }
    r = client.post("/api/v1/backtests", json=payload)
    assert r.status_code == 202, r.text
    body = r.json()
    assert "run_id" in body and isinstance(body["run_id"], str)
    assert body.get("status") == "queued"


# T061 ---------------------------------------------------------------------------
@pytest.mark.integration
@pytest.mark.feature006
def test_t061_backtest_run_request_validation_invalid_strategy() -> None:
    """T061: Backtest run request validation test.

    Uses existing legacy endpoint /backtest/run (pre-versioned) to ensure a domain
    validation rule is enforced (dual_sma fast < slow). This should already pass.
    """
    invalid_payload = {
        "ticker": "TEST",
        "timeframe": "1m",
        "start": "2024-01-01",
        "end": "2024-01-05",
        # Invalid because fast >= slow triggers RunConfig validator error
        "strategy_name": "dual_sma",
        "strategy_params": {"fast": 20, "slow": 10},
        "risk_model": "fixed_fraction",
        "risk_params": {"fraction": 0.1},
        "validation": {},
        "seed": 42,
    }
    r = client.post("/backtest/run", json=invalid_payload)
    # Pydantic validation error mapped to 400 by route logic
    assert r.status_code == 400, r.text
    body = r.json()
    assert "invalid configuration" in body.get("detail", "")


# T062 ---------------------------------------------------------------------------
@pytest.mark.integration
@pytest.mark.feature006
def test_t062_backtest_result_payload_shape() -> None:
    """T062: Backtest result payload shape test.

    After T069 the GET /api/v1/backtests/{run_id} should include equity_curve, metrics, trades_summary.
    Currently minimal status endpoint omits these fields.
    """
    # Create run via existing endpoint to obtain run_id
    valid_payload = {
        "ticker": "TEST",  # use synthetic dataset-supported symbol
        "timeframe": "1m",
        "start": "2024-01-01",
        "end": "2024-01-02",
        "strategy_name": "dual_sma",
        "strategy_params": {"fast": 5, "slow": 10},
        "risk_model": "fixed_fraction",
        "risk_params": {"fraction": 0.1},
        "validation": {},
    }
    create_resp = client.post("/backtest/run", json=valid_payload)
    assert create_resp.status_code == 201 or create_resp.status_code == 200
    run_id = create_resp.json()["run_id"]
    # Use versioned endpoint implemented in T069
    status_resp = client.get(f"/api/v1/backtests/{run_id}")
    assert status_resp.status_code == 200
    data = status_resp.json()
    for key in ["equity_curve", "metrics", "trades_summary"]:
        assert key in data, f"Missing key {key} (expected T069)"
    assert isinstance(data["equity_curve"], list)
    assert isinstance(data["metrics"], dict)
    assert isinstance(data["trades_summary"], dict)


# T078 ---------------------------------------------------------------------------
@pytest.mark.determinism
@pytest.mark.feature006
def test_t078_seed_and_strategy_hash_persisted() -> None:
    """T078: Deterministic seed and strategy hash persistence.

    Submits run with explicit seed, then fetches result to ensure seed & strategy_hash
    fields are present for future Monte Carlo determinism.
    """
    payload = {
        "symbol": "TEST",
        "date_range": {"start": "2024-02-01", "end": "2024-02-03"},
        "strategy": {"name": "dual_sma", "params": {"fast": 3, "slow": 9}},
        "risk": {
            "initial_equity": 5000,
            "position_sizing": "fixed_fraction",
            "fraction": 0.01,
        },
        "validation": {},
        "seed": 777,
    }
    r = client.post("/api/v1/backtests", json=payload)
    assert r.status_code == 202, r.text
    run_id = r.json()["run_id"]
    result = client.get(f"/api/v1/backtests/{run_id}")
    assert result.status_code == 200
    body = result.json()
    assert body.get("seed") == 777
    assert isinstance(body.get("strategy_hash"), str) and body[
        "strategy_hash"
    ].startswith("dual_sma:")


# T063 ---------------------------------------------------------------------------
@pytest.mark.determinism
@pytest.mark.feature006
def test_t063_monte_carlo_paths_determinism() -> None:
    """T063: Monte Carlo paths generation determinism test (activated after T070).

    Ensures that repeated calls with identical seed & path count produce identical
    equity_paths matrix and percentile arrays.
    """
    # Submit a run to obtain run_id
    payload = {
        "symbol": "TEST",
        "date_range": {"start": "2024-03-01", "end": "2024-03-05"},
        "strategy": {"name": "dual_sma", "params": {"fast": 4, "slow": 12}},
        "risk": {
            "initial_equity": 10000,
            "position_sizing": "fixed_fraction",
            "fraction": 0.02,
        },
        "validation": {},
        "seed": 111,
    }
    r = client.post("/api/v1/backtests", json=payload)
    assert r.status_code == 202, r.text
    run_id = r.json()["run_id"]

    mc_req = {"paths": 50, "seed": 999}
    r1 = client.post(f"/api/v1/backtests/{run_id}/montecarlo", json=mc_req)
    r2 = client.post(f"/api/v1/backtests/{run_id}/montecarlo", json=mc_req)
    assert r1.status_code == 200 and r2.status_code == 200
    d1, d2 = r1.json(), r2.json()
    assert d1["paths_meta"] == d2["paths_meta"]
    # Equity paths identical
    assert d1["equity_paths"] == d2["equity_paths"]
    assert d1["percentiles"] == d2["percentiles"]
    # Basic shape checks
    assert len(d1["equity_paths"]) == 50
    assert len(d1["equity_paths"][0]) > 0


# T071 ---------------------------------------------------------------------------
@pytest.mark.integration
@pytest.mark.feature006
def test_t071_run_history_listing_basic() -> None:
    """T071: Run history listing returns at least one run after submissions.

    Creates two runs with symbol TEST then queries listing filtered by symbol.
    """
    for seed in (201, 202):
        payload = {
            "symbol": "TEST",
            "date_range": {"start": "2024-03-10", "end": "2024-03-12"},
            "strategy": {"name": "dual_sma", "params": {"fast": 5, "slow": 15}},
            "risk": {
                "initial_equity": 8000,
                "position_sizing": "fixed_fraction",
                "fraction": 0.02,
            },
            "validation": {},
            "seed": seed,
        }
        r = client.post("/api/v1/backtests", json=payload)
        assert r.status_code == 202
    listing = client.get("/api/v1/backtests", params={"symbol": "TEST", "limit": 5})
    assert listing.status_code == 200, listing.text
    body = listing.json()
    assert body.get("symbol") == "TEST"
    assert isinstance(body.get("runs"), list) and len(body["runs"]) >= 2
    # Ensure required keys present in first run
    first = body["runs"][0]
    for key in ["run_id", "created_at", "status", "strategy"]:
        assert key in first


# T064 ---------------------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.feature006
def test_t064_walk_forward_splits_computation() -> None:
    """T064: Walk-forward splits computation test (activated after T072)."""
    # Create run
    payload = {
        "symbol": "TEST",
        "date_range": {"start": "2024-04-01", "end": "2024-04-05"},
        "strategy": {"name": "dual_sma", "params": {"fast": 3, "slow": 9}},
        "risk": {
            "initial_equity": 6000,
            "position_sizing": "fixed_fraction",
            "fraction": 0.01,
        },
        "validation": {},
        "seed": 555,
    }
    r = client.post("/api/v1/backtests", json=payload)
    assert r.status_code == 202
    run_id = r.json()["run_id"]
    wf = client.get(f"/api/v1/backtests/{run_id}/walkforward")
    assert wf.status_code == 200, wf.text
    data = wf.json()
    assert data.get("run_id") == run_id
    splits = data.get("splits")
    assert isinstance(splits, list)
    assert len(splits) >= 1
    first = splits[0]
    assert "train" in first and "test" in first


# T073 ---------------------------------------------------------------------------
@pytest.mark.integration
@pytest.mark.feature006
def test_t073_export_config_endpoint() -> None:
    """T073: Export config returns original request fields."""
    payload = {
        "symbol": "TEST",
        "date_range": {"start": "2024-05-01", "end": "2024-05-07"},
        "strategy": {"name": "dual_sma", "params": {"fast": 6, "slow": 18}},
        "risk": {
            "initial_equity": 12000,
            "position_sizing": "fixed_fraction",
            "fraction": 0.03,
        },
        "validation": {},
        "seed": 909,
    }
    r = client.post("/api/v1/backtests", json=payload)
    assert r.status_code == 202
    run_id = r.json()["run_id"]
    cfg = client.get(f"/api/v1/backtests/{run_id}/config")
    assert cfg.status_code == 200
    body = cfg.json()
    assert body.get("run_id") == run_id
    original = body.get("original_request")
    assert isinstance(original, dict)
    # Spot check a few keys
    assert original.get("symbol") == "TEST"
    assert original.get("strategy", {}).get("name") == "dual_sma"


# T065 ---------------------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.feature006
def test_t065_extended_percentiles_flag_true_adds_p5_p95() -> None:
    """T065: Extended percentiles test (active after T074)."""
    # Create run
    payload = {
        "symbol": "TEST",
        "date_range": {"start": "2024-06-01", "end": "2024-06-03"},
        "strategy": {"name": "dual_sma", "params": {"fast": 5, "slow": 15}},
        "risk": {
            "initial_equity": 9000,
            "position_sizing": "fixed_fraction",
            "fraction": 0.02,
        },
        "validation": {},
        "seed": 321,
    }
    r = client.post("/api/v1/backtests", json=payload)
    assert r.status_code == 202
    run_id = r.json()["run_id"]
    mc = client.post(
        f"/api/v1/backtests/{run_id}/montecarlo",
        json={"paths": 40, "extended_percentiles": True},
    )
    assert mc.status_code == 200, mc.text
    body = mc.json()
    ext = body.get("extended_percentiles")
    assert isinstance(ext, dict)
    assert "p5" in ext and "p95" in ext
    assert len(ext["p5"]) == len(body["percentiles"]["p50"])  # same horizon length


# T066 ---------------------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.feature006
def test_t066_advanced_validation_toggles_echo() -> None:
    """T066: Advanced validation toggles acceptance test (activated after T075).

    Submits run with extended_validation_toggles + advanced block and ensures
    they are echoed back in both result payload and export config endpoint.
    """
    payload = {
        "symbol": "TEST",
        "date_range": {"start": "2024-06-10", "end": "2024-06-12"},
        "strategy": {"name": "dual_sma", "params": {"fast": 4, "slow": 12}},
        "risk": {
            "initial_equity": 7000,
            "position_sizing": "fixed_fraction",
            "fraction": 0.02,
        },
        "validation": {},
        "extended_validation_toggles": {"sensitivity": True, "regime": False},
        "advanced": {"regime_flags": ["bull", "bear"]},
        "seed": 246,
    }
    r = client.post("/api/v1/backtests", json=payload)
    assert r.status_code == 202, r.text
    run_id = r.json()["run_id"]
    result = client.get(f"/api/v1/backtests/{run_id}")
    assert result.status_code == 200, result.text
    body = result.json()
    assert body.get("extended_validation_toggles", {}).get("sensitivity") is True
    assert body.get("extended_validation_toggles", {}).get("regime") is False
    adv = body.get("advanced")
    assert isinstance(adv, dict) and adv.get("regime_flags") == ["bull", "bear"]
    # Export config should also include these fields
    cfg = client.get(f"/api/v1/backtests/{run_id}/config")
    assert cfg.status_code == 200
    original = cfg.json().get("original_request")
    assert original.get("extended_validation_toggles", {}).get("sensitivity") is True
    assert original.get("advanced", {}).get("regime_flags") == ["bull", "bear"]


# ---------------------------------------------------------------------------
# Phase 3.5B Remediation Tests (Negative / Error Paths)
# T082-T086
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.feature006
def test_t082_backtest_submission_invalid_params() -> None:
    """T082: Invalid backtest params (missing dates & bad strategy param) -> 400.

    Cases:
    - Missing date_range.end
    - Strategy fast >= slow (invalid ordering)
    Expect consolidated 400 with detail message referencing invalid configuration.
    """
    payload = {
        "symbol": "TEST",
        "date_range": {"start": "2024-07-01"},  # end missing
        "strategy": {"name": "dual_sma", "params": {"fast": 30, "slow": 10}},  # invalid
        "risk": {
            "initial_equity": 10000,
            "position_sizing": "fixed_fraction",
            "fraction": 0.02,
        },
        "validation": {},
        "seed": 42,
    }
    r = client.post("/api/v1/backtests", json=payload)
    assert r.status_code == 400, r.text
    detail = r.json().get("detail", "").lower()
    assert "invalid" in detail or "fast" in detail


@pytest.mark.integration
@pytest.mark.feature006
def test_t083_backtest_submission_multi_ticker_attempt() -> None:
    """T083: Multi-ticker attempt (comma separated) should be rejected enforcing single ticker policy."""
    payload = {
        "symbol": "TEST,OTHER",
        "date_range": {"start": "2024-07-01", "end": "2024-07-05"},
        "strategy": {"name": "dual_sma", "params": {"fast": 5, "slow": 10}},
        "risk": {
            "initial_equity": 10000,
            "position_sizing": "fixed_fraction",
            "fraction": 0.02,
        },
        "validation": {},
        "seed": 11,
    }
    r = client.post("/api/v1/backtests", json=payload)
    assert r.status_code == 400, r.text
    assert "single" in r.json().get("detail", "").lower()


@pytest.mark.integration
@pytest.mark.feature006
def test_t084_candles_invalid_interval_and_symbol() -> None:
    """T084: Candles endpoint invalid interval & symbol normalization failure -> 400.

    Interval not in allowed set; symbol contains invalid characters.
    """
    r = client.get(
        "/api/v1/market/candles",
        params={
            "symbol": "@@BAD@@",
            "interval": "13min",  # unsupported
            "from_": "2024-07-01T00:00:00Z",
            "to": "2024-07-01T01:00:00Z",
            "limit": 10,
        },
    )
    assert r.status_code == 400, r.text
    txt = r.json().get("detail", "").lower()
    assert "interval" in txt or "symbol" in txt


@pytest.mark.integration
@pytest.mark.feature006
def test_t085_monte_carlo_invalid_paths_bounds() -> None:
    """T085: Monte Carlo invalid paths (<20 or >500) -> 400."""
    # Create a valid run first
    run_payload = {
        "symbol": "TEST",
        "date_range": {"start": "2024-07-10", "end": "2024-07-12"},
        "strategy": {"name": "dual_sma", "params": {"fast": 5, "slow": 15}},
        "risk": {
            "initial_equity": 5000,
            "position_sizing": "fixed_fraction",
            "fraction": 0.02,
        },
        "validation": {},
        "seed": 55,
    }
    r = client.post("/api/v1/backtests", json=run_payload)
    assert r.status_code == 202, r.text
    run_id = r.json()["run_id"]
    for paths in (0, 5, 501, 999):
        mc = client.post(
            f"/api/v1/backtests/{run_id}/montecarlo", json={"paths": paths}
        )
        assert mc.status_code == 400, mc.text
        assert "paths" in mc.json().get("detail", "").lower()


@pytest.mark.integration
@pytest.mark.feature006
def test_t086_rate_limiting_monte_carlo_burst() -> None:
    """T086: Burst Monte Carlo requests exceeding limit -> 429 for excess calls.

    Sends more than configured burst (assumed 8) quickly; expects at least one 429.
    """
    run_payload = {
        "symbol": "TEST",
        "date_range": {"start": "2024-07-15", "end": "2024-07-18"},
        "strategy": {"name": "dual_sma", "params": {"fast": 5, "slow": 15}},
        "risk": {
            "initial_equity": 7000,
            "position_sizing": "fixed_fraction",
            "fraction": 0.02,
        },
        "validation": {},
        "seed": 77,
    }
    r = client.post("/api/v1/backtests", json=run_payload)
    assert r.status_code == 202, r.text
    run_id = r.json()["run_id"]
    statuses: list[int] = []
    for _ in range(12):  # exceed 8 burst limit
        resp = client.post(f"/api/v1/backtests/{run_id}/montecarlo", json={"paths": 40})
        statuses.append(resp.status_code)
    assert any(s == 429 for s in statuses), f"Expected at least one 429, got {statuses}"
    # Ensure earlier successes still valid 200s
    assert any(s == 200 for s in statuses)

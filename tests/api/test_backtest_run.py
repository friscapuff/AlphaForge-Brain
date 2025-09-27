from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

# Ensure backend source directory is importable (alphaforge-brain/src)
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "alphaforge-brain" / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from api.app import create_app  # type: ignore  # noqa: E402


def _client() -> TestClient:
    app = create_app()
    return TestClient(app)


def test_create_backtest_run_happy_path():
    c = _client()
    now = datetime.now(timezone.utc)
    payload = {
        "ticker": "AAPL",
    "timeframe": "1d",
        "start": (now - timedelta(days=30)).date().isoformat(),
        "end": now.date().isoformat(),
        "strategy_name": "mean_rev",
        "strategy_params": {"lookback": 5},
        "risk_model": "basic",
        "risk_params": {"max_position_pct": 10},
        "validation": {"permutation": None, "block_bootstrap": None, "monte_carlo": None, "walk_forward": None},
    }
    r = c.post("/backtest/run", json=payload, headers={"x-correlation-id": "abc123"})
    assert r.status_code == 201, r.text
    data = r.json()
    assert "run_id" in data and isinstance(data["run_id"], str)
    assert data["created"] is True
    # Correlation id echo
    assert r.headers.get("x-correlation-id") == "abc123"


def test_create_backtest_run_invalid_date_order():
    c = _client()
    now = datetime.now(timezone.utc)
    payload = {
        "ticker": "AAPL",
    "timeframe": "1d",
        "start": now.date().isoformat(),
        "end": (now - timedelta(days=1)).date().isoformat(),  # invalid
        "strategy_name": "mean_rev",
        "strategy_params": {},
        "risk_model": "basic",
        "risk_params": {},
        "validation": {"permutation": None, "block_bootstrap": None, "monte_carlo": None, "walk_forward": None},
    }
    r = c.post("/backtest/run", json=payload)
    assert r.status_code == 422  # Pydantic validation error
    body = r.json()
    # Error should reference 'end'
    assert "end" in str(body)


def test_create_backtest_run_missing_ticker():
    c = _client()
    now = datetime.now(timezone.utc)
    payload = {
        "ticker": "",  # invalid blank
    "timeframe": "1d",
        "start": (now - timedelta(days=10)).date().isoformat(),
        "end": now.date().isoformat(),
        "strategy_name": "s1",
        "strategy_params": {},
        "risk_model": "basic",
        "risk_params": {},
        "validation": {"permutation": None, "block_bootstrap": None, "monte_carlo": None, "walk_forward": None},
    }
    r = c.post("/backtest/run", json=payload)
    assert r.status_code == 422
    assert "ticker" in r.text


def test_create_backtest_run_strategy_missing():
    c = _client()
    now = datetime.now(timezone.utc)
    payload = {
        "ticker": "MSFT",
    "timeframe": "1d",
        "start": (now - timedelta(days=5)).date().isoformat(),
        "end": now.date().isoformat(),
        # missing strategy_name => validation error
        "risk_model": "basic",
        "risk_params": {},
        "validation": {"permutation": None, "block_bootstrap": None, "monte_carlo": None, "walk_forward": None},
    }
    r = c.post("/backtest/run", json=payload)
    assert r.status_code == 422
    assert "strategy_name" in r.text


def test_create_backtest_run_unsupported_timeframe():  # T106
    c = _client()
    now = datetime.now(timezone.utc)
    payload = {
        "ticker": "AAPL",
        "timeframe": "7d",  # unsupported timeframe
        "start": (now - timedelta(days=10)).date().isoformat(),
        "end": now.date().isoformat(),
        "strategy_name": "mean_rev",
        "strategy_params": {"lookback": 5},
        "risk_model": "basic",
        "risk_params": {},
        "validation": {"permutation": None, "block_bootstrap": None, "monte_carlo": None, "walk_forward": None},
    }
    r = c.post("/backtest/run", json=payload)
    # parse_timeframe should raise -> our endpoint maps generic error to 400 or pydantic -> 400/422 acceptable
    assert r.status_code in (400, 422)
    assert "Unsupported timeframe" in r.text

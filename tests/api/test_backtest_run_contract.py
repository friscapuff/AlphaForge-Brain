from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from fastapi.testclient import TestClient

import sys

_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "alphaforge-brain" / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from api.app import create_app  # type: ignore  # noqa: E402


def _load_schema(name: str) -> dict:
    schema_path = _ROOT / "specs" / "006-begin-work-on" / "contracts" / name
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _client() -> TestClient:
    return TestClient(create_app())


def test_backtest_run_create_contract_shapes():  # T103
    request_schema = _load_schema("backtest-run-create-request.v1.schema.json")
    response_schema = _load_schema("backtest-run-create-response.v1.schema.json")

    # Basic schema sanity
    for sch in (request_schema, response_schema):
        assert sch.get("$schema")
        assert sch.get("type") == "object"

    # Build valid payload matching request schema fields
    now = datetime.now(timezone.utc)
    payload = {
        "ticker": "AAPL",
        "timeframe": "1d",
        "start": (now - timedelta(days=10)).date().isoformat(),
        "end": now.date().isoformat(),
        "strategy_name": "mean_rev",
        "strategy_params": {"lookback": 5},
        "risk_model": "basic",
        "risk_params": {"max_position_pct": 10},
        "validation": {"permutation": None, "block_bootstrap": None, "monte_carlo": None, "walk_forward": None},
        "seed": 42,
    }

    c = _client()
    r = c.post("/backtest/run", json=payload)
    assert r.status_code == 201, r.text
    body = r.json()
    # Response contract keys
    assert set(response_schema["required"]).issubset(body.keys())
    assert isinstance(body["run_id"], str)
    assert isinstance(body["created"], bool)

    # Negative: missing required -> 422
    bad_payload = payload.copy()
    del bad_payload["ticker"]
    r2 = c.post("/backtest/run", json=bad_payload)
    assert r2.status_code == 422

from __future__ import annotations

import os
from contextlib import contextmanager

import pytest
from api.app import app
from fastapi.testclient import TestClient


@contextmanager
def env_override(key: str, value: str | None):
    old = os.environ.get(key)
    try:
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
        yield
    finally:
        if old is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = old


client = TestClient(app)


@pytest.mark.unit
@pytest.mark.feature008
def test_t051_deferred_when_over_limit():
    payload = {
        "symbol": "T051SYM",
        "date_range": {"start": "2024-10-01", "end": "2024-10-15"},
        "strategy": {"name": "dual_sma", "params": {"fast": 5, "slow": 20}},
        "risk": {"initial_equity": 10000},
        "validation": {
            "walk_forward": {
                "optimization": {
                    "enabled": True,
                    "param_grid": {"fast": [5, 10, 20], "slow": [50, 100]},
                }
            }
        },
        # ensure advanced container exists to exercise warnings append path
        "advanced": {"regime_flags": ["bull"]},
    }
    with env_override("AF_OPTIMIZATION_MAX_COMBINATIONS", "4"):
        r = client.post("/api/v1/backtests", json=payload)
        assert r.status_code == 202, r.text
        run_id = r.json()["run_id"]
        res = client.get(f"/api/v1/backtests/{run_id}")
        assert res.status_code == 200
        body = res.json()
        assert body.get("optimization_mode") == "deferred"
        adv = body.get("advanced")
        assert isinstance(adv, dict)
        ws = adv.get("warnings")
        assert isinstance(ws, list) and any(
            w.get("code") == "OPTIMIZATION_DEFERRED" for w in ws
        )


@pytest.mark.unit
@pytest.mark.feature008
def test_t051_no_defer_when_under_limit():
    payload = {
        "symbol": "T051LOW",
        "date_range": {"start": "2024-10-01", "end": "2024-10-15"},
        "strategy": {"name": "dual_sma", "params": {"fast": 5, "slow": 20}},
        "risk": {"initial_equity": 10000},
        "validation": {
            "walk_forward": {
                "optimization": {
                    "enabled": True,
                    "param_grid": {"fast": [5], "slow": [50]},
                }
            }
        },
    }
    with env_override("AF_OPTIMIZATION_MAX_COMBINATIONS", "10"):
        r = client.post("/api/v1/backtests", json=payload)
        assert r.status_code == 202, r.text
        run_id = r.json()["run_id"]
        res = client.get(f"/api/v1/backtests/{run_id}")
        body = res.json()
        assert body.get("optimization_mode") in (None, "none")
        adv = body.get("advanced")
        if isinstance(adv, dict) and isinstance(adv.get("warnings"), list):
            assert not any(
                w.get("code") == "OPTIMIZATION_DEFERRED" for w in adv["warnings"]
            )  # no deferred warning

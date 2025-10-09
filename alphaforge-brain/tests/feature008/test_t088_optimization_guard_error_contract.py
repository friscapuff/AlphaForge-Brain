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
def test_t088_deferred_warning_contract_is_deterministic():
    """
    Large grid (combinations > limit) triggers deterministic warning object and optimization_mode='deferred'.

    Validates fields: code, combinations, limit. Ensures repeated GET returns identical payload subset.
    """
    payload = {
        "symbol": "T088SYM",
        "date_range": {"start": "2024-10-01", "end": "2024-10-15"},
        "strategy": {"name": "dual_sma", "params": {"fast": 5, "slow": 20}},
        "risk": {"initial_equity": 10000},
        "validation": {
            "walk_forward": {
                "optimization": {
                    # 3 x 3 = 9 combinations
                    "enabled": True,
                    "param_grid": {"fast": [5, 10, 20], "slow": [50, 100, 200]},
                }
            }
        },
        "advanced": {"regime_flags": ["bull"]},
    }
    with env_override("AF_OPTIMIZATION_MAX_COMBINATIONS", "6"):
        r = client.post("/api/v1/backtests", json=payload)
        assert r.status_code == 202, r.text
        run_id = r.json()["run_id"]

        res1 = client.get(f"/api/v1/backtests/{run_id}")
        res2 = client.get(f"/api/v1/backtests/{run_id}")
        assert res1.status_code == 200 and res2.status_code == 200
        b1, b2 = res1.json(), res2.json()

        for b in (b1, b2):
            assert b.get("optimization_mode") == "deferred"
            adv = b.get("advanced")
            assert isinstance(adv, dict) and isinstance(adv.get("warnings"), list)
            # Find the OPTIMIZATION_DEFERRED warning
            matches = [
                w for w in adv["warnings"] if w.get("code") == "OPTIMIZATION_DEFERRED"
            ]
            assert matches, f"warning not found in {adv}"
            w = matches[0]
            assert w.get("combinations") == 9
            assert w.get("limit") == 6

        # Deterministic subset equality (warnings array may include other future items; compare the first match)
        w1 = next(
            w
            for w in b1["advanced"]["warnings"]
            if w.get("code") == "OPTIMIZATION_DEFERRED"
        )
        w2 = next(
            w
            for w in b2["advanced"]["warnings"]
            if w.get("code") == "OPTIMIZATION_DEFERRED"
        )
        assert w1 == w2

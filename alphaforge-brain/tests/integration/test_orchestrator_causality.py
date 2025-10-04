from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
from domain.run.orchestrator import orchestrate
from domain.schemas.run_config import RiskSpec, RunConfig, StrategySpec
from domain.strategy.base import strategy as strategy_register
from services.causality_guard import CausalityMode

from infra import config as _config
from infra.db import get_connection
from infra.persistence import init_run


@strategy_register("peek_next_close_orch")
def _peek_next_close_orch(df: pd.DataFrame, params: dict | None = None) -> pd.DataFrame:
    # Intentionally peek forward to trigger causality guard when instrumentation active
    out = df.copy()
    out["signal"] = (out["close"].shift(-1) > out["close"]).astype("float")
    return out


def _cfg() -> RunConfig:
    return RunConfig(
        indicators=[],
        strategy=StrategySpec(name="peek_next_close_orch", params={}),
        risk=RiskSpec(model="fixed", params={}),
        symbol="TEST",
        timeframe="1m",
        start="2024-01-01",
        end="2024-01-02",
    )


def _setup_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    class _TempSettings(_config.Settings):
        sqlite_path: Path = tmp_path / "orchestrator_causality.db"

    try:
        _config.get_settings.cache_clear()  # type: ignore[attr-defined]
    except Exception:
        pass
    # Use pytest monkeypatch to avoid leaking state to other tests
    monkeypatch.setattr(_config, "get_settings", lambda: _TempSettings(), raising=False)

    run_hash = "d" * 64
    init_run(
        run_hash=run_hash,
        created_at_ms=1,
        status="pending",
        config_json={"cfg": 1},
        manifest_json={
            "schema_version": 1,
            "run_hash": run_hash,
            "db_version": 1,
            "created_at": 1,
            "updated_at": 1,
            "status": "pending",
            "data_hash": "2" * 64,
            "seed_root": 42,
            "provenance": {"manifest_content_hash": "3" * 64},
            "causality_guard": {"mode": "PERMISSIVE", "violations": 0},
            "bootstrap": {
                "seed": 1,
                "trials": 0,
                "ci_level": 0.95,
                "method": "simple",
                "fallback": True,
            },
        },
        data_hash="2" * 64,
        seed_root=42,
        db_version=1,
        bootstrap_seed=123,
        walk_forward_spec=None,
    )
    return run_hash


def test_orchestrator_strict_guard_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_hash = _setup_db(tmp_path, monkeypatch)
    cfg = _cfg()
    with pytest.raises(RuntimeError):
        orchestrate(cfg, guard_mode=CausalityMode.STRICT, run_hash=run_hash)


def test_orchestrator_permissive_persists_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_hash = _setup_db(tmp_path, monkeypatch)
    cfg = _cfg()
    res = orchestrate(cfg, guard_mode=CausalityMode.PERMISSIVE, run_hash=run_hash)
    assert isinstance(res, dict)

    with get_connection() as conn:
        rows = conn.execute(
            "SELECT key, value, phase FROM metrics WHERE run_hash=? AND key IN ('causality_mode','future_access_violations')",
            (run_hash,),
        ).fetchall()
        d = {}
        for k, v, p in rows:
            d[(k, p)] = v
        # Expect exactly the 'run' phase entries present
        assert d.get(("causality_mode", "run")) == CausalityMode.PERMISSIVE
        assert ("future_access_violations", "run") in d
        assert int(d[("future_access_violations", "run")]) > 0

        # Manifest causality block updated
        manifest = json.loads(
            conn.execute(
                "SELECT manifest_json FROM runs WHERE run_hash=?", (run_hash,)
            ).fetchone()[0]
        )
        cg = manifest.get("causality_guard", {})
        assert cg.get("mode") == CausalityMode.PERMISSIVE
        assert int(cg.get("violations", 0)) > 0

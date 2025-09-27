from __future__ import annotations

from pathlib import Path

from domain.run.orchestrator import Orchestrator, OrchestratorState
from domain.schemas.run_config import (
    ExecutionSpec,
    RiskSpec,
    RunConfig,
    StrategySpec,
    ValidationSpec,
)

from infra import config as _config
from infra.db import get_connection


def _config_with_validation() -> RunConfig:
    return RunConfig(
        indicators=[],
        strategy=StrategySpec(name="dual_sma", params={"fast": 5, "slow": 15}),
        risk=RiskSpec(model="fixed", params={"size": 1}),
        execution=ExecutionSpec(slippage_bps=0.0, fee_bps=0.0),
        validation=ValidationSpec(
            permutation={"n": 50},
            block_bootstrap={"n_iter": 50, "method": "hadj_bb"},
            walk_forward={"n_folds": 3},
        ),
        symbol="TEST",
        timeframe="1m",
        start="2023-01-01",
        end="2023-01-02",
        seed=123,
    )


def test_orchestrator_persists_validation_payload(sqlite_tmp_path, monkeypatch) -> None:
    # Point DB to temporary path for isolated schema with validation columns
    class _TempSettings(_config.Settings):
        sqlite_path: Path = sqlite_tmp_path

    try:
        _config.get_settings.cache_clear()  # type: ignore[attr-defined]
    except Exception:
        pass
    monkeypatch.setattr(_config, "get_settings", lambda: _TempSettings(), raising=False)
    cfg = _config_with_validation()
    orch = Orchestrator(cfg, seed=123, guard_mode="PERMISSIVE", run_hash="r" * 64)
    res = orch.run()
    assert orch.state == OrchestratorState.COMPLETE
    assert "validation" in res
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT payload_json, permutation_pvalue, bootstrap_method, bootstrap_block_length, bootstrap_jitter, bootstrap_fallback FROM validation WHERE run_hash=?",
            ("r" * 64,),
        ).fetchall()
        # Best-effort insert should exist with at least one row
        assert len(rows) >= 1
        payload = rows[0][0]
        assert isinstance(payload, str) and payload.startswith("{")

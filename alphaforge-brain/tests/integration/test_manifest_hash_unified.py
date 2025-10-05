from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from src.models.cost_model_config import CostModelConfig
from src.models.dataset_snapshot import DatasetSnapshot
from src.models.execution_config import ExecutionConfig, FillPolicy, RoundingMode
from src.models.feature_spec import FeatureSpec
from src.models.strategy_config import StrategyConfig
from src.models.validation_config import ValidationConfig
from src.services.manifest import build_manifest, collect_artifacts
from src.services.run_hash import compute_run_hash


def _make_config(seed: int = 1):
    ds = DatasetSnapshot(
        path="/tmp/data.csv",
        data_hash="hash123",
        calendar_id="NYSE",
        bar_count=100,
        first_ts=datetime(2024, 1, 1, tzinfo=timezone.utc),
        last_ts=datetime(2024, 1, 2, tzinfo=timezone.utc),
        gap_count=0,
        holiday_gap_count=0,
        duplicate_count=0,
    )
    strat = StrategyConfig(id="s", required_features=["ma"], parameters={"k": 1})
    exec_cfg = ExecutionConfig(
        fill_policy=FillPolicy.NEXT_BAR_OPEN,
        lot_size=1,
        rounding_mode=RoundingMode.ROUND,
    )
    cost_cfg = CostModelConfig(
        slippage_bps=0,
        spread_pct=None,
        participation_rate=None,
        fee_bps=0,
        borrow_cost_bps=0,
    )
    val_cfg = ValidationConfig(
        permutation_trials=10, seed=seed, caution_p_threshold=0.1
    )
    fs = FeatureSpec(
        name="ma", version="1", inputs=["close"], params={"w": 5}, shift_applied=1
    )
    from src.models.run_config import RunConfig

    return RunConfig(
        dataset=ds,
        features=[fs],
        strategy=strat,
        execution=exec_cfg,
        cost=cost_cfg,
        validation=val_cfg,
        walk_forward=None,
    )


@pytest.mark.integration
@pytest.mark.determinism
def test_manifest_hash_matches_service_and_is_order_independent(tmp_path: Path):
    p1 = tmp_path / "a.txt"
    p2 = tmp_path / "b.txt"
    p1.write_text("hello", encoding="utf-8")
    p2.write_text("world", encoding="utf-8")

    cfg = _make_config(seed=5)

    # Order 1
    artifacts1 = collect_artifacts([p1, p2])
    m1 = build_manifest("run-1", cfg, [p1, p2])
    rh1 = compute_run_hash(cfg, artifacts1)

    # Order 2 (reversed)
    artifacts2 = collect_artifacts([p2, p1])
    m2 = build_manifest("run-2", cfg, [p2, p1])
    rh2 = compute_run_hash(cfg, artifacts2)

    # Unification: all hashes must be equal regardless of artifact order
    assert m1.composite_hash == rh1
    assert m2.composite_hash == rh2
    assert m1.composite_hash == m2.composite_hash


@pytest.mark.integration
@pytest.mark.determinism
def test_manifest_hash_changes_with_seed(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("data", encoding="utf-8")

    cfg1 = _make_config(seed=1)
    cfg2 = _make_config(seed=2)

    m1 = build_manifest("r1", cfg1, [p])
    m2 = build_manifest("r2", cfg2, [p])

    assert m1.composite_hash != m2.composite_hash

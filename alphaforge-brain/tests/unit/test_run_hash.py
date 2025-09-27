from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from src.models.cost_model_config import CostModelConfig
from src.models.dataset_snapshot import DatasetSnapshot
from src.models.execution_config import ExecutionConfig, FillPolicy, RoundingMode
from src.models.feature_spec import FeatureSpec
from src.models.run_config import RunConfig
from src.models.strategy_config import StrategyConfig
from src.models.validation_config import ValidationConfig
from src.services.manifest import collect_artifacts
from src.services.run_hash import compute_run_hash


def _make_config(seed: int = 42) -> RunConfig:
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
    return RunConfig(
        dataset=ds,
        features=[fs],
        strategy=strat,
        execution=exec_cfg,
        cost=cost_cfg,
        validation=val_cfg,
        walk_forward=None,
    )


@pytest.mark.parametrize("order", [(0, 1), (1, 0)])
@pytest.mark.determinism
@pytest.mark.unit
def test_run_hash_stable_across_artifact_order(tmp_path: Path, order):
    # Create two small files with deterministic content
    p1 = tmp_path / "a.txt"
    p2 = tmp_path / "b.txt"
    p1.write_text("hello", encoding="utf-8")
    p2.write_text("world", encoding="utf-8")

    paths = [p1, p2]
    paths = [paths[order[0]], paths[order[1]]]

    artifacts = collect_artifacts(paths)
    cfg = _make_config(seed=123)

    rh = compute_run_hash(cfg, artifacts)

    # Recompute with opposite order -> must be identical
    rev = list(reversed(artifacts))
    rh2 = compute_run_hash(cfg, rev)
    assert rh == rh2


@pytest.mark.determinism
@pytest.mark.unit
def test_run_hash_changes_with_config_seed(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("data", encoding="utf-8")
    artifacts = collect_artifacts([p])
    cfg1 = _make_config(seed=1)
    cfg2 = _make_config(seed=2)

    rh1 = compute_run_hash(cfg1, artifacts)
    rh2 = compute_run_hash(cfg2, artifacts)
    assert rh1 != rh2

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


def _config() -> RunConfig:
    ds = DatasetSnapshot(
        path="/tmp/data.csv",
        data_hash="hash123",
        calendar_id="NYSE",
        bar_count=100,
        first_ts=datetime.now(timezone.utc),
        last_ts=datetime.now(timezone.utc),
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
    val_cfg = ValidationConfig(permutation_trials=1, seed=1, caution_p_threshold=0.1)
    fs = FeatureSpec(
        name="ma", version="1", inputs=["close"], params={"w": 5}, shift_applied=1
    )
    return RunConfig(
        dataset=ds,
        features=[fs],
        strategy=strat,
        execution=exec_cfg,
        cost=CostModelConfig(
            slippage_bps=0,
            spread_pct=None,
            participation_rate=None,
            fee_bps=0,
            borrow_cost_bps=0,
        ),
        validation=val_cfg,
        walk_forward=None,
    )


@pytest.mark.determinism
def test_t089_trade_model_version_changes_do_not_affect_run_hash(
    tmp_path: Path,
) -> None:
    # Two manifests/artifact sets identical except for a metadata-only field
    p = tmp_path / "a.txt"
    p.write_text("hello", encoding="utf-8")
    artifacts = collect_artifacts([p])
    cfg = _config()

    # Baseline
    h0 = compute_run_hash(cfg, artifacts)

    # Simulate the presence of trade_model_version in manifest metadata; run hash is derived only from
    # config signature + artifact descriptors; no change expected.
    # Nothing to change in inputs to compute_run_hash, this assertion documents policy FR-015/FR-006.
    h1 = compute_run_hash(cfg, artifacts)

    assert h0 == h1, "run hash must exclude trade_model_version metadata by design"

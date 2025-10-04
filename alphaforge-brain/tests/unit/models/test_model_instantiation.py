from datetime import datetime, timezone

from models.cost_model_config import CostModelConfig
from models.dataset_snapshot import DatasetSnapshot
from models.execution_config import ExecutionConfig
from models.feature_spec import FeatureSpec
from models.run_config import RunConfig
from models.strategy_config import StrategyConfig
from models.validation_config import ValidationConfig
from models.walk_forward_config import (
    WalkForwardConfig,
    WalkForwardOptimizationConfig,
    WalkForwardRobustnessConfig,
    WalkForwardSegmentConfig,
)


def _base():
    ds = DatasetSnapshot(
        path="/tmp/nvda.parquet",
        data_hash="abc123",
        calendar_id="NYSE",
        bar_count=120,
        first_ts=datetime(2025, 1, 1, tzinfo=timezone.utc),
        last_ts=datetime(2025, 1, 2, tzinfo=timezone.utc),
        gap_count=0,
        holiday_gap_count=0,
        duplicate_count=0,
    )
    strat = StrategyConfig(
        id="dual_sma",
        parameters={"fast": 5, "slow": 10},
        required_features=["sma_fast", "sma_slow"],
    )
    exec_cfg = ExecutionConfig(
        fill_policy="NEXT_BAR_OPEN", lot_size=1, rounding_mode="FLOOR"
    )
    cost = CostModelConfig(slippage_bps=0, fee_bps=0, borrow_cost_bps=0)
    feats = [
        FeatureSpec(
            name="sma_fast",
            version="1",
            inputs=["close"],
            params={"window": 5},
            shift_applied=False,
        ),
        FeatureSpec(
            name="sma_slow",
            version="1",
            inputs=["close"],
            params={"window": 10},
            shift_applied=False,
        ),
    ]
    val = ValidationConfig(permutation_trials=10, seed=42, caution_p_threshold=0.05)
    wf = WalkForwardConfig(
        segment=WalkForwardSegmentConfig(train_bars=100, test_bars=20, warmup_bars=10),
        optimization=WalkForwardOptimizationConfig(enabled=False, param_grid={}),
        robustness=WalkForwardRobustnessConfig(compute=False),
    )
    return ds, strat, exec_cfg, cost, feats, val, wf


def test_run_config_deterministic_signature_stable():
    ds, strat, exec_cfg, cost, feats, val, wf = _base()
    rc = RunConfig(
        dataset=ds,
        strategy=strat,
        execution=exec_cfg,
        cost=cost,
        features=feats,
        validation=val,
        walk_forward=wf,
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    sig1 = rc.deterministic_signature()
    # Reorder features -> signature should remain stable
    rc2 = rc.model_copy(update={"features": list(reversed(feats))})
    assert rc2.deterministic_signature() == sig1


def test_run_config_provenance_tuple_length():
    ds, strat, exec_cfg, cost, feats, val, wf = _base()
    rc = RunConfig(
        dataset=ds,
        strategy=strat,
        execution=exec_cfg,
        cost=cost,
        features=feats,
        validation=val,
        walk_forward=wf,
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    pt = rc.provenance_tuple()
    assert isinstance(pt, tuple)
    assert len(pt) > 5

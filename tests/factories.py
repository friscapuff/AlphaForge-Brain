from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any

from src.models.cost_model_config import CostModelConfig
from src.models.dataset_snapshot import DatasetSnapshot
from src.models.execution_config import ExecutionConfig, FillPolicy, RoundingMode
from src.models.feature_spec import FeatureSpec
from src.models.run_config import RunConfig
from src.models.strategy_config import StrategyConfig
from src.models.trade import Trade, TradeSide
from src.models.validation_config import ValidationConfig
from src.models.validation_result import ValidationResult
from src.models.walk_forward_config import (
    WalkForwardConfig,
    WalkForwardOptimizationConfig,
    WalkForwardRobustnessConfig,
    WalkForwardSegmentConfig,
)

# -------- Core primitive factories --------

def dataset_snapshot(**overrides: Any) -> DatasetSnapshot:
    base = dict(
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
    base.update(overrides)
    return DatasetSnapshot(**base)


def strategy_config(**overrides: Any) -> StrategyConfig:
    base = dict(id="strat", required_features=[], parameters={})
    base.update(overrides)
    return StrategyConfig(**base)


def execution_config(**overrides: Any) -> ExecutionConfig:
    base = dict(fill_policy=FillPolicy.NEXT_BAR_OPEN, lot_size=1, rounding_mode=RoundingMode.ROUND)
    base.update(overrides)
    return ExecutionConfig(**base)


def cost_config(**overrides: Any) -> CostModelConfig:
    base = dict(slippage_bps=0, spread_pct=None, participation_rate=None, fee_bps=0, borrow_cost_bps=0)
    base.update(overrides)
    return CostModelConfig(**base)


def validation_config(**overrides: Any) -> ValidationConfig:
    base = dict(permutation_trials=0, seed=1, caution_p_threshold=0.1)
    base.update(overrides)
    return ValidationConfig(**base)


def walk_forward_config(**overrides: Any) -> WalkForwardConfig:
    base = dict(
        segment=WalkForwardSegmentConfig(train_bars=50, test_bars=10, warmup_bars=0),
        optimization=WalkForwardOptimizationConfig(enabled=True, param_grid={"a": [1, 2]}),
        robustness=WalkForwardRobustnessConfig(compute=True),
    )
    base.update(overrides)
    return WalkForwardConfig(**base)


def feature_spec(name: str = "feat", version: str = "v1", inputs: Sequence[str] | None = None, **overrides: Any) -> FeatureSpec:
    base = dict(name=name, version=version, inputs=list(inputs) if inputs else [], params={}, shift_applied=True)
    base.update(overrides)
    return FeatureSpec(**base)


def walk_forward_variant(train: int, test: int, warmup: int = 0, **overrides: Any) -> WalkForwardConfig:
    return walk_forward_config(
        segment=WalkForwardSegmentConfig(train_bars=train, test_bars=test, warmup_bars=warmup),
        **overrides,
    )


def run_config(**overrides: Any) -> RunConfig:
    base = dict(
        dataset=dataset_snapshot(),
        features=[feature_spec()],
        strategy=strategy_config(),
        execution=execution_config(),
        cost=cost_config(),
        validation=validation_config(),
        walk_forward=None,
    )
    base.update(overrides)
    return RunConfig(**base)


def trade(price: float = 100.0, qty: float = 1.0, side: TradeSide = TradeSide.BUY, **overrides: Any) -> Trade:
    base = dict(ts=datetime.now(timezone.utc), symbol="XYZ", price=price, quantity=qty, side=side, strategy_id="strat")
    base.update(overrides)
    return Trade(**base)


def validation_result(p: float | None = 0.5, **overrides: Any) -> ValidationResult:
    base = dict(metric_name="metric", observed_value=1.0, p_value=p, permutation_distribution=[])
    base.update(overrides)
    return ValidationResult(**base)

__all__ = [
    "cost_config",
    "dataset_snapshot",
    "execution_config",
    "run_config",
    "strategy_config",
    "trade",
    "validation_config",
    "validation_result",
    "walk_forward_config",
]

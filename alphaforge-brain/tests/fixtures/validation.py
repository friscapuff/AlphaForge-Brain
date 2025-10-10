from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np
import pandas as pd
from src.models.cost_model_config import CostModelConfig
from src.models.dataset_snapshot import DatasetSnapshot
from src.models.execution_config import ExecutionConfig, FillPolicy, RoundingMode
from src.models.feature_spec import FeatureSpec
from src.models.run_config import RunConfig
from src.models.strategy_config import StrategyConfig
from src.models.validation_config import ValidationConfig
from src.models.walk_forward_config import (
    WalkForwardConfig,
    WalkForwardOptimizationConfig,
    WalkForwardRobustnessConfig,
    WalkForwardSegmentConfig,
)

DEFAULT_VALIDATION_SEED_ROOT = 0x010AF043


@dataclass(frozen=True)
class ValidationSeedBundle:
    """Deterministic seed context for validation modules."""

    seed_root: int
    permutation: tuple[int, ...]
    optimizer: int
    cross_validation: int
    realism: int

    def as_mapping(self) -> Mapping[str, int | tuple[int, ...]]:
        return {
            "seed_root": self.seed_root,
            "permutation": self.permutation,
            "optimizer": self.optimizer,
            "cross_validation": self.cross_validation,
            "realism": self.realism,
        }


@dataclass(frozen=True)
class ValidationFixtureBundle:
    """Aggregate bundle returned by :func:`validation_fixtures`."""

    bars: pd.DataFrame
    run_config: RunConfig
    seeds: ValidationSeedBundle


def synthetic_validation_bars(
    count: int = 360,
    seed: int = DEFAULT_VALIDATION_SEED_ROOT,
) -> pd.DataFrame:
    """Return deterministic OHLCV bars for validation tests.

    The series emulates mildly trending equity with heteroskedastic noise so that
    permutation and cross-validation routines have repeatable yet non-trivial
    inputs.
    """

    rng = np.random.default_rng(seed)
    index = pd.date_range("2022-01-01", periods=count, freq="1h")
    trend = np.linspace(100.0, 108.0, count)
    noise = rng.normal(loc=0.0, scale=0.35, size=count)
    close = trend + noise
    open_ = close - rng.normal(loc=0.02, scale=0.05, size=count)
    high = np.maximum(open_, close) + rng.uniform(0.01, 0.35, size=count)
    low = np.minimum(open_, close) - rng.uniform(0.01, 0.30, size=count)
    volume = rng.integers(5_000, 12_000, size=count)

    frame = pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume.astype(float),
        },
        index=index,
    )
    frame.index.name = "timestamp"
    return frame


def seeded_optimizer_config() -> WalkForwardOptimizationConfig:
    """Deterministic optimizer grid used by walk-forward fixtures."""

    return WalkForwardOptimizationConfig(
        enabled=True,
        param_grid={
            "lookback": [20, 40, 60],
            "vol_target": [0.5, 0.75],
            "penalty": [0.0, 0.1],
        },
    )


def seeded_walk_forward_config() -> WalkForwardConfig:
    """Provide a deterministic walk-forward configuration used by validation tests."""

    return WalkForwardConfig(
        segment=WalkForwardSegmentConfig(train_bars=160, test_bars=40, warmup_bars=20),
        optimization=seeded_optimizer_config(),
        robustness=WalkForwardRobustnessConfig(compute=True),
    )


def seeded_validation_config(
    *,
    permutation_trials: int = 128,
    seed: int = DEFAULT_VALIDATION_SEED_ROOT,
    caution_threshold: float = 0.01,
) -> ValidationConfig:
    """Return ValidationConfig with deterministic defaults for Masters validation tests."""

    return ValidationConfig(
        seed=seed,
        permutation_count=permutation_trials,
        significance_threshold=caution_threshold,
        leakage_threshold=0.1,
        realism_capacity_bps_limit=500,
    )


def deterministic_validation_seeds(
    *,
    permutations: int,
    seed_root: int = DEFAULT_VALIDATION_SEED_ROOT,
) -> ValidationSeedBundle:
    """Derive deterministic seeds for validation submodules.

    Generates a reproducible permutation seed vector along with component seeds for
    optimizer restarts, cross-validation, and execution realism so tests can assert
    consistent behaviour across runs.
    """

    rng = np.random.default_rng(seed_root)
    permutation = tuple(int(v) for v in rng.integers(0, 2**31 - 1, size=permutations))
    optimizer = int(rng.integers(0, 2**31 - 1))
    cross_validation = int(rng.integers(0, 2**31 - 1))
    realism = int(rng.integers(0, 2**31 - 1))
    return ValidationSeedBundle(
        seed_root=seed_root,
        permutation=permutation,
        optimizer=optimizer,
        cross_validation=cross_validation,
        realism=realism,
    )


def validation_fixtures(
    *,
    seed_root: int = DEFAULT_VALIDATION_SEED_ROOT,
    permutation_trials: int = 128,
    bar_count: int = 360,
) -> ValidationFixtureBundle:
    """Convenience helper returning the canonical validation fixture bundle."""

    bars = synthetic_validation_bars(count=bar_count, seed=seed_root)
    seeds = deterministic_validation_seeds(
        permutations=permutation_trials, seed_root=seed_root
    )
    config = RunConfig(
        dataset=DatasetSnapshot(
            path="/tmp/validation.csv",
            data_hash="validation-fixture-hash",
            calendar_id="NYSE",
            bar_count=bar_count,
            first_ts=bars.index[0].to_pydatetime(),
            last_ts=bars.index[-1].to_pydatetime(),
            gap_count=0,
            holiday_gap_count=0,
            duplicate_count=0,
        ),
        features=[
            FeatureSpec(
                name="validation_feature",
                version="v1",
                inputs=["close"],
                params={"window": 15},
                shift_applied=True,
            )
        ],
        strategy=StrategyConfig(
            id="validation-strategy",
            required_features=["validation_feature"],
            parameters={"risk_target": 0.1},
        ),
        execution=ExecutionConfig(
            fill_policy=FillPolicy.NEXT_BAR_OPEN,
            lot_size=1,
            rounding_mode=RoundingMode.ROUND,
        ),
        cost=CostModelConfig(
            slippage_bps=5,
            spread_pct=None,
            participation_rate=0.1,
            fee_bps=1,
            borrow_cost_bps=0,
        ),
        validation=seeded_validation_config(
            permutation_trials=permutation_trials, seed=seed_root
        ),
        walk_forward=seeded_walk_forward_config(),
    )

    # Ensure the config respects deterministic feature ordering for downstream
    # signature comparisons.
    return ValidationFixtureBundle(bars=bars, run_config=config, seeds=seeds)


__all__ = [
    "DEFAULT_VALIDATION_SEED_ROOT",
    "ValidationFixtureBundle",
    "ValidationSeedBundle",
    "deterministic_validation_seeds",
    "seeded_validation_config",
    "seeded_optimizer_config",
    "seeded_walk_forward_config",
    "synthetic_validation_bars",
    "validation_fixtures",
]

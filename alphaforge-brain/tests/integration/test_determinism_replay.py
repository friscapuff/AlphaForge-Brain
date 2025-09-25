from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
from src.domain.execution import simulator
from src.domain.risk.engine import apply_risk
from src.domain.schemas.run_config import (
    ExecutionSpec,
    IndicatorSpec,
    RiskSpec,
    RunConfig,
    StrategySpec,
    ValidationSpec,
)
from src.domain.strategy.runner import run_strategy
from src.infra.utils.seed import derive_seed


def _candles(n: int = 60) -> pd.DataFrame:
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rows = []
    price = 100.0
    for i in range(n):
        price += np.sin(i / 5.0) * 0.2
        rows.append(
            {
                "timestamp": base + timedelta(minutes=i),
                "open": price,
                "high": price + 0.2,
                "low": price - 0.2,
                "close": price,
                "volume": 1000 + i,
            }
        )
    return pd.DataFrame(rows)


def _config(seed: int = 123) -> RunConfig:
    return RunConfig(
        indicators=[
            IndicatorSpec(name="dual_sma", params={"short_window": 3, "long_window": 8})
        ],
        strategy=StrategySpec(
            name="dual_sma", params={"short_window": 3, "long_window": 8}
        ),
        risk=RiskSpec(model="fixed_fraction", params={"fraction": 0.5}),
        execution=ExecutionSpec(fee_bps=0.0, slippage_bps=0.0),
        validation=ValidationSpec(n_permutation=0, seed=seed),
        symbol="TEST",
        timeframe="1m",
        start="2024-01-01",
        end="2024-01-02",
        seed=seed,
    )


def test_two_runs_identical_outputs() -> None:
    df = _candles(120)
    cfg = _config(seed=42)
    sized1 = apply_risk(cfg, run_strategy(cfg, df, candle_hash="h", cache_root=None))
    fills1, pos1 = simulator.simulate(cfg, sized1)

    # Simulate re-run with same inputs
    cfg2 = _config(seed=42)
    sized2 = apply_risk(cfg2, run_strategy(cfg2, df, candle_hash="h", cache_root=None))
    fills2, pos2 = simulator.simulate(cfg2, sized2)

    pd.testing.assert_frame_equal(sized1, sized2)
    pd.testing.assert_frame_equal(fills1, fills2)
    pd.testing.assert_frame_equal(pos1, pos2)


def test_derive_seed_stability_across_subseeds() -> None:
    base = 99
    s0 = derive_seed(base, namespace="perm", index=0)
    s1 = derive_seed(base, namespace="perm", index=1)
    s2 = derive_seed(base, namespace="perm", index=2)
    assert len({s0, s1, s2}) == 3
    assert s0 == derive_seed(base, namespace="perm", index=0)

from __future__ import annotations

# Ensure indicator + strategy modules load (registration side-effects)
import domain.indicators.sma
import domain.strategy.dual_sma  # noqa: F401  # ensure registration
import numpy as np
import pandas as pd
import pytest
from domain.strategy.base import StrategyRegistry


def test_dual_sma_strategy_signals() -> None:
    data = pd.DataFrame(
        {
            "close": pd.Series(
                [100, 101, 102, 103, 104, 103, 102, 101, 102, 103, 104, 105],
                dtype=float,
            )
        }
    )

    # We'll rely on indicator having already produced columns externally in real pipeline.
    # For unit strategy test we mimic by computing small windows first.
    from domain.indicators.sma import dual_sma_indicator

    enriched = dual_sma_indicator(data, {"short_window": 3, "long_window": 5})

    strat = StrategyRegistry.get("dual_sma")
    result = strat(enriched, params={"short_window": 3, "long_window": 5})

    # Expect a 'signal' column of {-1,0,1}
    assert "signal" in result.columns
    assert set(result["signal"].dropna().unique()).issubset({-1, 0, 1})

    # Define expected first crossover behaviour: when short SMA first exceeds long SMA -> +1
    first_long_valid = 4  # long=5 window valid index
    # Find first index where short > long after both valid
    idx_cross: int | None = None
    for i in range(first_long_valid, len(result)):
        s = result.loc[i, "sma_short_3"]
        long_sma = result.loc[i, "sma_long_5"]
        if not np.isnan(s) and not np.isnan(long_sma) and s > long_sma:
            idx_cross = i
            break
    assert idx_cross is not None
    assert result.loc[idx_cross, "signal"] == 1

    # After short drops below long we expect -1 at first occurence
    idx_cross_down: int | None = None
    for i in range(idx_cross + 1, len(result)):
        s = result.loc[i, "sma_short_3"]
        long_sma = result.loc[i, "sma_long_5"]
        if not np.isnan(s) and not np.isnan(long_sma) and s < long_sma:
            idx_cross_down = i
            break
    assert idx_cross_down is not None
    assert result.loc[idx_cross_down, "signal"] == -1

    # Determinism: second call identical
    result2 = strat(enriched.copy(), params={"short_window": 3, "long_window": 5})
    pd.testing.assert_frame_equal(result, result2)


def test_dual_sma_strategy_validation_errors() -> None:
    from domain.indicators.sma import dual_sma_indicator

    data = pd.DataFrame(
        {"close": pd.Series([100, 101, 102, 103, 104, 103, 102], dtype=float)}
    )
    enriched = dual_sma_indicator(data, {"short_window": 2, "long_window": 4})
    strat = StrategyRegistry.get("dual_sma")

    # Require SMA columns present
    missing = enriched.drop(
        columns=next(c for c in enriched.columns if c.startswith("sma_short"))
    )
    with pytest.raises(ValueError):
        strat(missing, params={"short_window": 2, "long_window": 4})

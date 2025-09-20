import numpy as np
import pandas as pd
import pytest

# Import the SMA module to trigger registration side-effects
import domain.indicators.sma  # noqa: F401
from domain.indicators.registry import IndicatorRegistry
from domain.indicators.sma import SimpleMovingAverage  # ensure class available


def test_dual_sma_indicator_basic():
    # Synthetic price series
    prices = pd.Series([100,101,102,103,104,105,106,107,108,109], name="close", dtype=float)

    # Expect short=3, long=5 SMA columns created with precise rolling means
    indicator = IndicatorRegistry.get("dual_sma")

    df = pd.DataFrame({"close": prices})
    out = indicator(df, params={"short_window": 3, "long_window": 5})

    assert "sma_short_3" in out.columns, "short SMA column missing"
    assert "sma_long_5" in out.columns, "long SMA column missing"

    # First valid short SMA index = 2 (0-based), value = mean(100,101,102) = 101.0
    assert out.loc[2, "sma_short_3"] == pytest.approx(101.0)
    # First valid long SMA index = 4, mean(100..104) = 102.0
    assert out.loc[4, "sma_long_5"] == pytest.approx(102.0)

    # Later sample check for determinism
    short_calc = np.mean([105,106,107])  # rows 5,6,7
    assert out.loc[7, "sma_short_3"] == pytest.approx(short_calc)

    # Windows must not be mutated across calls (idempotence / pure)
    out2 = indicator(df, params={"short_window": 3, "long_window": 5})
    pd.testing.assert_frame_equal(out, out2)


def test_dual_sma_indicator_validation_errors():
    prices = pd.DataFrame({"close": pd.Series([1,2,3,4,5], dtype=float)})
    indicator = IndicatorRegistry.get("dual_sma")

    # short >= 1, long > short
    with pytest.raises(ValueError):
        indicator(prices, params={"short_window": 0, "long_window": 5})
    with pytest.raises(ValueError):
        indicator(prices, params={"short_window": 5, "long_window": 4})
    with pytest.raises(ValueError):
        indicator(prices, params={"short_window": 3, "long_window": 3})


def test_simple_moving_average_basic():
    df = pd.DataFrame({"close": [10, 11, 12, 13, 14]}, dtype=float)
    sma = SimpleMovingAverage(window=3)
    out = sma.compute(df)
    col = "SMA_3_close"
    assert col in out.columns
    # First two rows should be NaN (need full window)
    assert out.loc[0, col] != out.loc[0, col]  # NaN check
    assert out.loc[1, col] != out.loc[1, col]
    # Third row mean(10,11,12)=11
    assert out.loc[2, col] == pytest.approx(11.0)
    # Fourth row mean(11,12,13)=12
    assert out.loc[3, col] == pytest.approx(12.0)
    # Idempotence
    out2 = sma.compute(df)
    pd.testing.assert_frame_equal(out, out2)


def test_simple_moving_average_errors():
    with pytest.raises(ValueError):
        SimpleMovingAverage(window=0)
    sma = SimpleMovingAverage(window=2)
    with pytest.raises(ValueError):
        sma.compute(pd.DataFrame({"open": [1, 2, 3]}))

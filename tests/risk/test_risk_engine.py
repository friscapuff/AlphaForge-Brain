from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

from domain.schemas.run_config import IndicatorSpec, RiskSpec, RunConfig, StrategySpec
from domain.strategy.runner import run_strategy


def _candles(n=120):
    base = datetime(2024,1,1,tzinfo=timezone.utc)
    rows = []
    price = 100.0
    for i in range(n):
        price += (1 if i % 8 < 4 else -1) * 0.5
        rows.append({
            "timestamp": base + timedelta(minutes=i),
            "open": price,
            "high": price + 0.2,
            "low": price - 0.2,
            "close": price,
            "volume": 100 + i,
        })
    return pd.DataFrame(rows)


def _config(fraction=0.1):
    return RunConfig(
        indicators=[IndicatorSpec(name="dual_sma", params={"fast":5,"slow":20})],
        strategy=StrategySpec(name="dual_sma", params={"short_window":5,"long_window":20}),
        risk=RiskSpec(model="fixed_fraction", params={"fraction": fraction}),
        symbol="TEST",
        timeframe="1m",
        start="2024-01-01",
        end="2024-02-01",
    )


def _signals_df():
    cfg = _config()
    df = _candles(150)
    signals = run_strategy(cfg, df, candle_hash="dummy", cache_root=None)
    return cfg, signals


def test_fixed_fraction_basic():
    cfg, signals = _signals_df()
    from domain.risk.engine import apply_risk
    out = apply_risk(cfg, signals)
    assert "position_size" in out.columns, "position_size column missing"
    valid = out["signal"].notna()
    assert (out.loc[valid, "position_size"] >= 0).all()
    out2 = apply_risk(cfg, signals)
    pd.testing.assert_frame_equal(out, out2)


def test_zero_nan_price_rows():
    cfg, signals = _signals_df()
    from domain.risk.engine import apply_risk
    mutated = signals.copy()
    mutated.loc[mutated.index[:3], "close"] = 0.0
    mutated.loc[mutated.index[3:6], "close"] = np.nan
    out = apply_risk(cfg, mutated)
    assert (out.loc[out.index[:6], "position_size"] == 0).all()


def test_invalid_fraction():
    bad_cfg = _config(fraction=1.5)
    _, signals = _signals_df()
    with pytest.raises(ValueError):
        from domain.risk.engine import apply_risk
        apply_risk(bad_cfg, signals)

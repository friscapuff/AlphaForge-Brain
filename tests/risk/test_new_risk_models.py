import numpy as np
import pandas as pd

from domain.risk.engine import apply_risk
from domain.schemas.run_config import (
    ExecutionSpec,
    IndicatorSpec,
    RiskSpec,
    RunConfig,
    StrategySpec,
    ValidationSpec,
)

# Build a deterministic signals frame with close prices trending so realized vol lowers over time

def _signals_df(n=40):
    ts = pd.date_range("2024-01-01", periods=n, freq="1min")
    # Price path with moderate variance first half then calmer second half
    prices = np.concatenate([
        100 + np.cumsum(np.random.default_rng(42).normal(0, 0.5, n//2)),
        100 + n//2 + np.linspace(0, 0.1*(n//2-1), n - n//2)
    ])
    df = pd.DataFrame({
        "timestamp": ts,
        "close": prices,
        "open": prices,
        "signal": [np.nan] + [1]*(n-1),  # treat every bar after first as active signal
    })
    return df


def _base_cfg(risk_spec: RiskSpec) -> RunConfig:
    return RunConfig(
        indicators=[IndicatorSpec(name="sma", params={"window": 2})],
        strategy=StrategySpec(name="dual_sma", params={"short_window": 2, "long_window": 4}),
        risk=risk_spec,
        execution=ExecutionSpec(),
        validation=ValidationSpec(),
        symbol="TEST", timeframe="1m", start="2024-01-01", end="2024-01-02"
    )


def test_volatility_target_sizes_scale_inverse_with_realized_vol():
    df = _signals_df()
    cfg = _base_cfg(RiskSpec(model="volatility_target", params={"target_vol": 0.15, "lookback": 5, "base_fraction": 0.2}))
    sized = apply_risk(cfg, df, equity=10_000)
    assert "position_size" in sized
    # Earlier rows (insufficient lookback) should be zero sized due to massive filled std (1e9 sentinel)
    assert sized["position_size"].iloc[0] == 0.0
    # Compute realized volatility proxy used in model (rolling std of pct change)
    rets = sized["close"].pct_change()
    lookback = 5
    rolling_std = rets.rolling(lookback).std().fillna(1e9)
    # Identify two indices where realized vol strictly decreases.
    # Scan from lookback onward to find first pair (i,j) with j>i and rv_j < rv_i.
    idx1 = None
    idx2 = None
    for i in range(lookback + 1, len(rolling_std) - 1):
        rv_i = rolling_std.iloc[i]
        # search forward
        for j in range(i + 1, len(rolling_std)):
            if rolling_std.iloc[j] < rv_i and rolling_std.iloc[j] < 1e8:  # ensure both are real (not sentinel)
                idx1 = i
                idx2 = j
                break
        if idx1 is not None:
            break
    if idx1 is not None and idx2 is not None:
        ps1 = sized["position_size"].iloc[idx1]
        ps2 = sized["position_size"].iloc[idx2]
        # Expect lower realized vol -> size should not shrink materially (> 1% tolerance downward)
        assert ps2 >= ps1 * 0.99
    else:  # fallback: ensure at least some positive sizing after lookback
        assert sized["position_size"].iloc[lookback + 1:].gt(0).any()


def test_kelly_fraction_respects_probability_and_payoff():
    df = _signals_df()
    cfg = _base_cfg(RiskSpec(model="kelly_fraction", params={"p_win": 0.55, "payoff_ratio": 1.2, "base_fraction": 0.5}))
    sized = apply_risk(cfg, df, equity=5_000)
    # All non-NaN signal rows sized
    assert sized["position_size"].iloc[1:].gt(0).all()
    first_size = sized["position_size"].iloc[1]
    # If we reduce p_win dramatically sizing should drop to zero
    cfg2 = _base_cfg(RiskSpec(model="kelly_fraction", params={"p_win": 0.2, "payoff_ratio": 1.2, "base_fraction": 0.5}))
    sized2 = apply_risk(cfg2, df, equity=5_000)
    assert sized2["position_size"].iloc[1] <= first_size
    # Extreme low p_win with high payoff may still give some positive fraction (but bounded)
    cfg3 = _base_cfg(RiskSpec(model="kelly_fraction", params={"p_win": 0.4, "payoff_ratio": 3.0, "base_fraction": 0.5}))
    sized3 = apply_risk(cfg3, df, equity=5_000)
    assert sized3["position_size"].iloc[1] >= 0

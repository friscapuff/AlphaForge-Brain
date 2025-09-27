from __future__ import annotations

import pandas as pd

from domain.risk.engine import apply_risk
from domain.schemas.run_config import RunConfig, StrategySpec, RiskSpec


def _cfg(model: str) -> RunConfig:
    return RunConfig(
        symbol="TEST",
        timeframe="1m",
        start="2024-01-01T00:00:00Z",
        end="2024-01-01T00:05:00Z",
        strategy=StrategySpec(name="buy_hold", params={}),
        risk=RiskSpec(model=model, params={}),
    )


def _signals_df() -> pd.DataFrame:
    ts = pd.date_range("2024-01-01", periods=5, freq="1min", tz="UTC")
    epoch_ms = (ts.view('int64') // 10**6).astype('int64')
    return pd.DataFrame({
        "timestamp": epoch_ms,
        "open": [100,101,102,103,104],
        "high": [101,102,103,104,105],
        "low":  [99,100,101,102,103],
        "close":[100.5,101.5,102.5,103.5,104.5],
        "volume":[1000,1000,1000,1000,1000],
        "signal":[1,1,1,1,1],
    })


def test_risk_none_passthrough_all_zero_sizes():
    cfg = _cfg("none")
    df = _signals_df()
    out = apply_risk(cfg, df, equity=50_000)
    assert "position_size" in out.columns
    assert all(v == 0.0 for v in out.position_size.tolist())
    # ensure original columns retained
    for col in ["timestamp","open","close","signal"]:
        assert col in out.columns


def test_risk_none_idempotent():
    cfg = _cfg("none")
    df = _signals_df()
    out1 = apply_risk(cfg, df, equity=10_000)
    out2 = apply_risk(cfg, df, equity=20_000)  # equity param should not matter for none
    assert out1.position_size.equals(out2.position_size)

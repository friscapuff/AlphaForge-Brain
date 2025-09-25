from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd
from _pytest.monkeypatch import MonkeyPatch
from domain.schemas.run_config import IndicatorSpec, RiskSpec, RunConfig, StrategySpec
from domain.strategy.runner import RunnerStats, run_strategy

# We will import runner after creation; for now expect domain.strategy.runner.run_strategy
# Using dual_sma strategy which expects SMA columns already present (via indicators / feature engine)


def _build_candles(n: int = 120) -> pd.DataFrame:
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rows = []
    price = 100.0
    for i in range(n):
        # simple deterministic walk
        price += (1 if i % 10 < 5 else -1) * 0.5
        rows.append(
            {
                "timestamp": base + timedelta(minutes=i),
                "open": price,
                "high": price + 0.2,
                "low": price - 0.2,
                "close": price,
                "volume": 100 + i,
            }
        )
    return pd.DataFrame(rows)


def _run_config(short: int = 5, long: int = 20) -> RunConfig:
    return RunConfig(
        indicators=[
            IndicatorSpec(name="dual_sma", params={"fast": short, "slow": long})
        ],
        strategy=StrategySpec(
            name="dual_sma", params={"short_window": short, "long_window": long}
        ),
        risk=RiskSpec(model="fixed", params={}),
        symbol="TEST",
        timeframe="1m",
        start="2024-01-01",
        end="2024-03-01",
    )


def test_signals_deterministic_and_aligned(monkeypatch: MonkeyPatch) -> None:
    from domain.features.engine import build_features as real_build_features

    calls: dict[str, int] = {"count": 0}

    def wrapper(df: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
        calls["count"] += 1
        return real_build_features(df, **kwargs)

    monkeypatch.setattr("domain.features.engine.build_features", wrapper)

    df = _build_candles(150)
    cfg = _run_config()
    # Ensure indicator registration side-effects loaded
    import domain.indicators.sma  # noqa: F401

    stats1 = RunnerStats()
    out1 = run_strategy(
        cfg, df, candle_hash="dummy", cache_root="./.tmp_cache", stats=stats1
    )
    assert "signal" in out1.columns
    # All timestamps should be sorted ascending and tz-aware
    assert out1["timestamp"].is_monotonic_increasing
    assert out1["timestamp"].dt.tz is not None
    # Determine deterministic hash like behavior by re-running (feature build should occur again because we monkeypatched wrapper)
    stats2 = RunnerStats()
    out2 = run_strategy(
        cfg, df, candle_hash="dummy", cache_root="./.tmp_cache", stats=stats2
    )
    pd.testing.assert_frame_equal(out1, out2)
    # Feature builder called at least once; with cache may still call twice due to absence of feature cache key specifics in test env
    assert calls["count"] >= 1


def test_empty_on_insufficient_warmup() -> None:
    # Provide fewer rows than long window so strategy should yield no valid signals (empty or all NaN without signal column)
    short = 5
    long = 30
    df = _build_candles(long - 5)  # insufficient for long SMA fully valid
    cfg = _run_config(short, long)

    out = run_strategy(cfg, df, candle_hash="dummy", cache_root=None)
    # Expect either empty output (no valid signals) or a signal column with all NaN
    if len(out) == 0:
        assert True
    else:
        assert "signal" in out.columns
        assert out["signal"].notna().sum() == 0


def test_feature_reuse(monkeypatch: MonkeyPatch) -> None:
    # Ensure if we pass precomputed features, internal feature build isn't called
    from domain.features.engine import build_features as real_build_features

    df = _build_candles(120)
    cfg = _run_config()

    features = real_build_features(df, use_cache=False)
    import domain.indicators.sma  # noqa: F401

    calls: dict[str, int] = {"count": 0}

    def counting(df: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
        calls["count"] += 1
        return real_build_features(df, **kwargs)

    monkeypatch.setattr("domain.features.engine.build_features", counting)

    # Pass precomputed features to ensure no new feature build call
    out = run_strategy(cfg, df, features=features, use_feature_cache=False)
    assert "signal" in out.columns
    assert (
        calls["count"] == 0
    ), "Feature build should not have been invoked when features provided"

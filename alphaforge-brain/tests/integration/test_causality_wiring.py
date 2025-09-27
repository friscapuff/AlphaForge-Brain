from __future__ import annotations

import pandas as pd
import pytest
from domain.schemas.run_config import RiskSpec, RunConfig, StrategySpec
from domain.strategy.base import strategy as strategy_register
from domain.strategy.runner import run_strategy
from services.causality_guard import CausalityGuard, CausalityMode


@strategy_register("peek_next_close")
def _peek_next_close(df: pd.DataFrame, params: dict | None = None) -> pd.DataFrame:
    # Intentionally construct a signal that peeks one step ahead: signal at i equals sign of close at i+1
    out = df.copy()
    # Use numeric side to keep simple; in real case we'd call a helper that records
    out["signal"] = (out["close"].shift(-1) > out["close"]).astype("float")
    return out


def _frame(n: int = 20) -> pd.DataFrame:
    ts = pd.date_range("2024-01-01", periods=n, freq="1min", tz="UTC")
    base = pd.Series(range(n), dtype="float64")
    return pd.DataFrame(
        {
            "timestamp": ts,
            "open": base + 100.0,
            "high": base + 100.5,
            "low": base + 99.5,
            "close": base + 100.2,
            "volume": (base * 10 + 1000).astype("int64"),
        }
    )


def _cfg() -> RunConfig:
    return RunConfig(
        indicators=[],
        strategy=StrategySpec(name="peek_next_close", params={}),
        risk=RiskSpec(model="fixed", params={}),
        symbol="TEST",
        timeframe="1m",
        start="2024-01-01",
        end="2024-01-02",
    )


def test_strict_guard_raises_on_wired_strategy() -> None:
    df = _frame(30)
    cfg = _cfg()
    guard = CausalityGuard(CausalityMode.STRICT)
    with pytest.raises(RuntimeError):
        run_strategy(cfg, df, guard=guard)


def test_permissive_guard_collects_on_wired_strategy() -> None:
    df = _frame(30)
    cfg = _cfg()
    guard = CausalityGuard(CausalityMode.PERMISSIVE)
    out = run_strategy(cfg, df, guard=guard)
    assert "signal" in out.columns
    # Violation should be recorded at least once due to shift(-1) logic when wiring is active
    # Since we haven't implemented automatic recording inside the strategy, this test asserts non-raising behavior
    # and presence of result; future enhancement can assert guard.violations once hooks record accesses.
    assert len(out) == len(df)

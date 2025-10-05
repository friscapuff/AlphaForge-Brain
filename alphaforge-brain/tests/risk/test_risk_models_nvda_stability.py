from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from domain.risk.engine import apply_risk
from domain.schemas.run_config import (
    ExecutionSpec,
    IndicatorSpec,
    RiskSpec,
    RunConfig,
    StrategySpec,
    ValidationSpec,
)


@pytest.fixture(scope="module")
def nvda_slice(
    nvda_canonical: tuple[pd.DataFrame, dict[str, object]],
) -> pd.DataFrame:  # Provided by shared fixture
    """Provide a deterministic head slice of the canonical NVDA dataset.

    Falls back to pytest.skip if dataset file not present (mirrors other NVDA tests pattern).
    """
    # The root conftest dynamically exposes nvda_canonical; if dataset missing that fixture asserts.
    # To be defensive (in case collection ordering differs) we duplicate the existence check and skip early.
    csv_primary = Path("data") / "NVDA_5y.csv"
    csv_alt = Path("src") / "domain" / "data" / "NVDA_5y.csv"
    if not csv_primary.exists() and not csv_alt.exists():
        pytest.skip("NVDA dataset not present; skipping risk stability tests.")
    df, _meta = nvda_canonical  # provided by tests/data/conftest.py
    head = df.iloc[:300].copy()
    assert len(head) >= 100
    return head


def _base_cfg(model: str, params: dict[str, Any]) -> RunConfig:
    return RunConfig(
        indicators=[IndicatorSpec(name="sma", params={"window": 5})],
        strategy=StrategySpec(
            name="dual_sma", params={"short_window": 5, "long_window": 20}
        ),
        risk=RiskSpec(model=model, params=params),
        execution=ExecutionSpec(),
        validation=ValidationSpec(),
        symbol="NVDA",
        timeframe="1m",
        start="2020-01-01",
        end="2020-12-31",
    )


def test_risk_models_size_positive_when_signal_and_price(
    nvda_slice: pd.DataFrame,
) -> None:
    # Build a deterministic signal column (all ones after first row)
    df = nvda_slice.copy()
    df["signal"] = pd.Series([math.nan] + [1] * (len(df) - 1), index=df.index)

    equity = 50_000.0

    fixed_cfg = _base_cfg("fixed_fraction", {"fraction": 0.05})
    fixed = apply_risk(fixed_cfg, df, equity=equity)

    vol_cfg = _base_cfg(
        "volatility_target", {"target_vol": 0.15, "lookback": 30, "base_fraction": 0.2}
    )
    vol = apply_risk(vol_cfg, df, equity=equity)

    kelly_cfg = _base_cfg(
        "kelly_fraction", {"p_win": 0.55, "payoff_ratio": 1.5, "base_fraction": 0.5}
    )
    kelly = apply_risk(kelly_cfg, df, equity=equity)

    # For rows after warmup, expect positive sizes for fixed and kelly
    assert (fixed["position_size"].iloc[10:] > 0).all()
    assert (kelly["position_size"].iloc[1:] >= 0).all()

    # Volatility target: After lookback window passes, some positive sizes expected
    assert vol["position_size"].iloc[31:].gt(0).any()

    # Determinism: rerun volatility and ensure identical sizing vector
    vol2 = apply_risk(vol_cfg, df, equity=equity)
    pd.testing.assert_series_equal(vol["position_size"], vol2["position_size"])

    # Scaling sanity: when realized volatility drops later, sizes should not systematically shrink
    # Compare median size of last 50 rows vs previous 50 rows (after warmup)
    tail_median = vol["position_size"].iloc[-50:].median()
    prev_median = vol["position_size"].iloc[-100:-50].median()
    # Realized volatility may increase causing smaller sizes; ensure not catastrophic (>50% drop)
    if prev_median > 0:
        assert tail_median >= prev_median * 0.5


@pytest.mark.parametrize("p_win,payoff", [(0.55, 1.5), (0.6, 1.2), (0.4, 3.0)])
def test_kelly_monotonic_with_probability(
    nvda_slice: pd.DataFrame, p_win: float, payoff: float
) -> None:
    df = nvda_slice.copy()
    df["signal"] = pd.Series([math.nan] + [1] * (len(df) - 1), index=df.index)
    equity = 25_000.0

    base_fraction = 0.5
    cfg = _base_cfg(
        "kelly_fraction",
        {"p_win": p_win, "payoff_ratio": payoff, "base_fraction": base_fraction},
    )
    sized = apply_risk(cfg, df, equity=equity)

    # Reference fraction calculation for second bar (first sized)
    price = df["close"].iloc[1]
    from domain.risk.engine import _kelly_fraction_size

    expected = _kelly_fraction_size(equity, float(price), p_win, payoff, base_fraction)
    assert pytest.approx(sized["position_size"].iloc[1], rel=1e-9) == expected

    # Probability sensitivity: lowering p_win reduces size (holding payoff constant)
    if p_win > 0.3:
        lower_cfg = _base_cfg(
            "kelly_fraction",
            {
                "p_win": max(0.01, p_win - 0.2),
                "payoff_ratio": payoff,
                "base_fraction": base_fraction,
            },
        )
        lower = apply_risk(lower_cfg, df, equity=equity)
        assert lower["position_size"].iloc[1] <= sized["position_size"].iloc[1] + 1e-9

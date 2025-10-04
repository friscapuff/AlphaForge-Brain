from typing import Any

import numpy as np
import pandas as pd
from domain.validation.runner import run_all


def build_trades(n: int = 20) -> pd.DataFrame:
    # Minimal trades DataFrame with timestamp and pnl for permutation/bootstrap etc.
    ts = pd.date_range("2024-01-01", periods=n, freq="1h")
    # Alternate small gains/losses
    pnl = np.where(np.arange(n) % 2 == 0, 1.0, -0.5)
    return pd.DataFrame({"timestamp": ts, "pnl": pnl})


def build_positions(n: int = 20) -> pd.DataFrame:
    ts = pd.date_range("2024-01-01", periods=n, freq="1h")
    equity = 100 + np.cumsum(np.where(np.arange(n) % 2 == 0, 1.0, -0.5))
    return pd.DataFrame({"timestamp": ts, "equity": equity})


def test_validation_run_all_deterministic() -> None:
    trades = build_trades(30)
    positions = build_positions(30)
    config = {
        "permutation": {"samples": 20},
        "block_bootstrap": {"samples": 15, "blocks": 3},
        "monte_carlo": {"paths": 25, "model": "normal", "params": {"scale": 0.01}},
        "walk_forward": {"folds": 3, "method": "expanding"},
    }
    result1 = run_all(trades, positions, seed=12345, config=config)
    result2 = run_all(trades, positions, seed=12345, config=config)

    def normalize(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: normalize(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [normalize(v) for v in obj]
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return obj

    assert normalize(result1) == normalize(result2), "Deterministic with same seed"

    # Key presence checks
    for key in [
        "permutation",
        "block_bootstrap",
        "monte_carlo_slippage",
        "walk_forward",
        "summary",
        "seed",
    ]:
        assert key in result1
    assert "p_value" in result1["permutation"]
    assert "distribution" in result1["block_bootstrap"]
    assert "distribution" in result1["monte_carlo_slippage"]
    assert "folds" in result1["walk_forward"] and "summary" in result1["walk_forward"]
    assert result1["summary"]["walk_forward_folds"] == len(
        result1["walk_forward"]["folds"]
    )


def test_validation_missing_sections_defaults() -> None:
    trades = build_trades(10)
    positions = build_positions(10)
    res = run_all(trades, positions, seed=1, config={})
    # Default sections should have placeholder values
    assert res["permutation"]["p_value"] is None
    assert res["block_bootstrap"]["distribution"] == []
    assert res["monte_carlo_slippage"]["observed"] is None
    assert res["walk_forward"]["summary"]["n_folds"] == 0

from __future__ import annotations

import numpy as np
import pandas as pd
from domain.validation.runner import run_all


def _flat_trades(n: int = 30) -> pd.DataFrame:
    # Low-variance positive returns to produce narrow CI
    ts = np.arange(n)
    rets = np.full(n, 0.001)
    qty = np.ones(n)
    entry = np.ones(n) * 100.0
    pnl = rets * qty * entry
    return pd.DataFrame(
        {
            "exit_ts": ts,
            "qty": qty,
            "entry_price": entry,
            "pnl": pnl,
            "return_pct": rets,
        }
    )


def test_gate_allows_when_under_width() -> None:
    trades = _flat_trades()
    cfg = {
        "block_bootstrap": {"n_iter": 100},
        "gates": {"block_bootstrap": {"max_ci_width": 0.2}},
    }
    res = run_all(trades, None, seed=123, config=cfg)
    assert res["summary"]["block_bootstrap_ci_width"] is not None
    assert res["summary"].get("block_bootstrap_gate_passed") is True


def test_gate_raises_when_over_width() -> None:
    # Use noisy trades to ensure non-zero CI width
    rng = np.random.default_rng(7)
    n = 60
    ts = np.arange(n)
    rets = rng.normal(0.0, 0.01, size=n)
    qty = np.ones(n)
    entry = np.ones(n) * 100.0
    pnl = rets * qty * entry
    trades = pd.DataFrame(
        {
            "exit_ts": ts,
            "qty": qty,
            "entry_price": entry,
            "pnl": pnl,
            "return_pct": rets,
        }
    )
    # Force a very small threshold to trigger failure
    cfg = {
        "block_bootstrap": {"n_iter": 50},
        "gates": {"block_bootstrap": {"max_ci_width": 1e-9}},
    }
    res = run_all(trades, None, seed=123, config=cfg)
    assert res["summary"].get("block_bootstrap_gate_passed") is False

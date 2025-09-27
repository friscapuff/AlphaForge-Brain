from __future__ import annotations

import numpy as np
import pandas as pd
from domain.validation.runner import run_all


def _fake_trades(n: int = 50, seed: int = 123) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    ts = np.arange(n)
    # synthetic per-trade pct returns with slight edge
    rets = rng.normal(0.001, 0.01, size=n)
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


def test_validation_runner_seeded_reproducible() -> None:
    trades = _fake_trades()
    cfg = {
        "permutation": {"n": 200},
        "block_bootstrap": {"n_iter": 300, "method": "hadj_bb"},
        "monte_carlo": {"n_iter": 200},
        "walk_forward": {"n_folds": 5},
    }
    r1 = run_all(trades, None, seed=42, config=cfg)
    r2 = run_all(trades, None, seed=42, config=cfg)
    # Deterministic scalar fields
    assert r1["seed"] == r2["seed"] == 42
    assert r1["permutation"]["p_value"] == r2["permutation"]["p_value"]
    assert r1["block_bootstrap"]["p_value"] == r2["block_bootstrap"]["p_value"]
    assert r1["block_bootstrap"].get("ci") == r2["block_bootstrap"].get("ci")
    assert r1["block_bootstrap"].get("trials") == r2["block_bootstrap"].get("trials")
    assert r1["walk_forward"]["summary"] == r2["walk_forward"]["summary"]
    # Arrays/lists equality
    import numpy as _np

    d1 = r1["block_bootstrap"]["distribution"]
    d2 = r2["block_bootstrap"]["distribution"]
    assert isinstance(d1, _np.ndarray) and isinstance(d2, _np.ndarray)
    assert _np.array_equal(d1, d2)
    s1 = r1["permutation"]["samples"]
    s2 = r2["permutation"]["samples"]
    assert s1 == s2
    # Sanity on shapes
    assert isinstance(r1["permutation"].get("p_value"), float)
    assert "distribution" in r1["block_bootstrap"]
    assert r1["walk_forward"]["summary"]["n_folds"] == 5

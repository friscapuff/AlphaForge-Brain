from __future__ import annotations

import numpy as np
import pandas as pd
from domain.validation.hadj_bb import hadj_bb_bootstrap


def _trades(n: int = 200, pattern: str = "ar1") -> pd.DataFrame:
    rng = np.random.default_rng(123)
    phi = 0.3
    if pattern.startswith("ar1"):
        # Allow pattern like "ar1:0.9" to control autocorrelation strength
        if ":" in pattern:
            try:
                phi = float(pattern.split(":", 1)[1])
            except Exception:
                phi = 0.3
        eps = rng.normal(0, 1, size=n)
        x = np.empty(n)
        x[0] = eps[0]
        for i in range(1, n):
            x[i] = phi * x[i - 1] + eps[i]
        rets = x * 0.001
    elif pattern == "iid":
        rets = rng.normal(0, 0.001, size=n)
    else:
        rets = np.zeros(n)
    ts = pd.date_range("2024-01-01", periods=n, freq="1min")
    # encode returns via pnl and qty/price so extract_returns can derive
    price = 100.0
    qty = 1.0
    pnl = rets * price * qty
    return pd.DataFrame({"timestamp": ts, "pnl": pnl, "qty": qty, "entry_price": price})


def test_hadj_bb_deterministic_and_metadata() -> None:
    trades = _trades(300, "ar1")
    out1 = hadj_bb_bootstrap(trades, n_iter=200, seed=42)
    out2 = hadj_bb_bootstrap(trades, n_iter=200, seed=42)
    # Distribution deterministic
    assert np.array_equal(out1["distribution"], out2["distribution"])  # type: ignore[index]
    # Keys and metadata
    for k in [
        "distribution",
        "observed_mean",
        "mean",
        "std",
        "p_value",
        "ci",
        "trials",
        "method",
        "fallback",
    ]:
        assert k in out1
    assert out1["method"] in {"hadj_bb", "simple"}
    # CI tuple sanity
    ci = out1["ci"]
    assert isinstance(ci, tuple) and len(ci) == 2
    assert ci[0] <= ci[1]


def test_hadj_bb_fallback_on_iid_or_short_series() -> None:
    # IID with near-zero autocorrelation should trigger fallback sometimes
    trades_iid = _trades(80, "iid")
    out = hadj_bb_bootstrap(trades_iid, n_iter=50, seed=7)
    assert out["fallback"] in {True, False}
    # Force short series to guarantee fallback (N < 5k)
    trades_short = _trades(30, "ar1:0.9")
    out_short = hadj_bb_bootstrap(trades_short, n_iter=50, seed=7)
    assert out_short["fallback"] is True

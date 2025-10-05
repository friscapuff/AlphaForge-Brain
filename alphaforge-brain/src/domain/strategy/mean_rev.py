"""Minimal mean reversion demo strategy used for tests.

Registered under name 'mean_rev'. Produces a trivial signal that flips
between +1 and -1 every bar after an initial warmup of 1 row.

This is ONLY for test coverage (retention policy multi-strategy ranking) and
is intentionally simple & deterministic.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from .base import strategy


@strategy("mean_rev")
def mean_rev_strategy(
    df: pd.DataFrame, params: dict[str, Any] | None = None
) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    out = df.copy()
    n = len(out)
    # Alternate +1 / -1 starting at second row; first row NaN warmup to mimic indicator delay
    import numpy as np

    signal = np.full(n, float("nan"))
    for i in range(1, n):
        signal[i] = 1 if (i % 2) == 0 else -1
    out["signal"] = signal
    return out


__all__ = ["mean_rev_strategy"]

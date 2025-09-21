from __future__ import annotations

import time
from datetime import datetime

import pandas as pd

from infra.time.timestamps import to_epoch_ms

__all__ = ["to_utc_ms", "utc_ms"]


def utc_ms() -> int:
    """Current UTC time in epoch milliseconds."""
    return int(time.time() * 1000)


def to_utc_ms(dt: datetime) -> int:
    """Convert a single datetime to UTC epoch ms using the centralized vectorized helper.

    This ensures identical semantics (naive treated as UTC, tz-aware normalized) and future
    enhancements (DST handling, masking) automatically apply here.
    """
    series = pd.Series([dt])
    out = to_epoch_ms(series)
    # Guarantee Python int return (may be pandas nullable Int64 if NaT)
    val = out.iloc[0]
    if pd.isna(val):  # pragma: no cover - defensive; callers not expected to pass NaT
        raise ValueError("NaT datetime provided to to_utc_ms")
    return int(val)

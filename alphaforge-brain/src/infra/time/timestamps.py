"""Central timestamp conversion helpers.

Provides stable, pandas-friendly utilities for converting datetime-like Series/Index to
UTC epoch millisecond int64 values while handling:
- Naive vs tz-aware inputs (assume a provided or default timezone for naive)
- DatetimeIndex or Series interchangeably
- Optional clipping to now (future filtering)

These helpers reduce repeated patterns and avoid deprecated usage (.view("int64")).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Literal, Union

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from zoneinfo import ZoneInfo

AmbiguousType = Union[Literal["infer", "NaT", "raise"], NDArray[np.bool_]]
NonExistentType = Union[
    Literal["shift_forward", "shift_backward", "NaT", "raise"], timedelta
]


def to_epoch_ms(
    values: pd.Series | pd.DatetimeIndex,
    *,
    assume_tz: str | None = None,
    clip_future: bool = False,
    ambiguous: AmbiguousType = "raise",
    nonexistent: NonExistentType = "raise",
) -> pd.Series:
    """Convert datetime-like values to UTC epoch milliseconds (int64) with DST safety.

    Behavior goals:
    - Accept Series or DatetimeIndex of naive or tz-aware timestamps (object or datetime64 dtypes).
    - If input is naive and assume_tz provided, localize using pandas.tz_localize semantics with
      explicit DST disambiguation via `ambiguous` and `nonexistent` parameters.
    - If input is naive and assume_tz is None, interpret as UTC (explicitly localize to UTC).
    - Preserve NaT values (they become pd.NA in the integer output Series) without raising.
    - Optionally drop future timestamps when clip_future=True (useful for defensive ingestion).
    - Provide deterministic int64 output (name preserved if Series input).

    DST / clock-change edge cases:
    - ambiguous: Passed directly to tz_localize. Defaults to 'raise' so tests can assert behavior.
      Typical alternative is 'NaT' or bool mask.
    - nonexistent: Passed directly; defaults to 'raise'. Typical alternative strategies include
      'shift_forward', 'NaT', or a Timedelta to add.

    Parameters
    ----------
    values : pd.Series | pd.DatetimeIndex
        Datetime-like input.
    assume_tz : str | None
        Timezone name (IANA) to apply to naive values; if None treat naive as UTC.
    clip_future : bool
        Remove timestamps > now (UTC) after conversion.
    ambiguous : see pandas.DatetimeIndex.tz_localize
        Handling for ambiguous (e.g., repeated) times at DST fall-back.
    nonexistent : see pandas.DatetimeIndex.tz_localize
        Handling for non-existent times at DST spring-forward.
    """
    # Fast path: empty
    if isinstance(values, (pd.Series, pd.DatetimeIndex)) and len(values) == 0:
        return pd.Series(dtype="Int64")  # pandas nullable integer

    # Normalize to DatetimeIndex (retain original index for Series)
    orig_index = getattr(values, "index", None)
    # Parse to object Series first to allow mixed tz handling safely
    # If all values appear naive and no assume_tz specified, we can parse with utc=True directly
    # to avoid pandas mixed-timezone FutureWarning and gain a vectorized fast path.
    try:
        if assume_tz is None:
            parsed = pd.to_datetime(values, utc=True, errors="coerce")
        else:
            parsed = pd.to_datetime(values, utc=False, errors="coerce")
    except Exception:  # fallback conservative path
        parsed = pd.to_datetime(values, utc=False, errors="coerce")
    if isinstance(parsed, pd.DatetimeIndex):
        parsed_series = parsed.to_series(index=orig_index)
    else:
        parsed_series = parsed  # already Series

    # Normalize each element to UTC preserving NaT; mixed tz-aware/naive supported
    norm_list: list[pd.Timestamp] = []
    for v in parsed_series.tolist():  # iteration size small in tests; acceptable
        if pd.isna(v):  # NaT
            norm_list.append(pd.NaT)
            continue
        ts = v
        if getattr(ts, "tzinfo", None) is None:
            if assume_tz:
                # mypy: pandas typeshed is conservative; runtime accepts broader ambiguous/nonexistent.
                ts = pd.DatetimeIndex(
                    [ts]
                ).tz_localize(  # pandas accepts our broader runtime types
                    ZoneInfo(assume_tz), ambiguous=ambiguous, nonexistent=nonexistent
                )[
                    0
                ]
            else:
                # Localize naive timestamp directly to UTC
                ts = ts.tz_localize("UTC")
        # Convert any tz-aware (localized above or already) to UTC (skip NaT)
        if not pd.isna(ts):
            ts = ts.astimezone(ZoneInfo("UTC"))
        norm_list.append(ts)
    dti = pd.DatetimeIndex(norm_list)

    # Preserve original NaT positions prior to localization
    orig_is_nat = pd.isna(dti)

    dt_utc_full = dti  # already UTC-normalized element-wise

    # Vectorized epoch ms (pandas stubs lack precise typing for view)
    epoch_ms_array = dt_utc_full.view("int64") // 1_000_000
    out: pd.Series = pd.Series(
        epoch_ms_array, index=orig_index, name=getattr(values, "name", None)
    )
    if orig_is_nat.any():
        out = out.astype("Int64")
        out[orig_is_nat] = pd.NA
    else:
        out = out.astype("int64")

    if clip_future and len(out):
        import time

        now_ms = int(time.time() * 1000)
        # Keep NA values (provenance of missing) while filtering future timestamps
        mask = (out <= now_ms) | out.isna()
        out = out[mask]

    # Reset index only if original input lacked a stable index (DatetimeIndex path). Keep Series index.
    if isinstance(values, pd.DatetimeIndex):
        out = out.reset_index(drop=True)
    return out


__all__ = ["to_epoch_ms"]

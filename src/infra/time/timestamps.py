from __future__ import annotations

import pandas as pd
from zoneinfo import ZoneInfo

"""Central timestamp conversion helpers.

Provides stable, pandas-friendly utilities for converting datetime-like Series/Index to
UTC epoch millisecond int64 values while handling:
- Naive vs tz-aware inputs (assume a provided or default timezone for naive)
- DatetimeIndex or Series interchangeably
- Optional clipping to now (future filtering)

These helpers reduce repeated patterns and avoid deprecated usage (.view("int64")).
"""


def to_epoch_ms(
    values: pd.Series | pd.DatetimeIndex,
    *,
    assume_tz: str | None = None,
    clip_future: bool = False,
    ambiguous: str | int | bool | pd.Series | None = "raise",
    nonexistent: str | int | pd.Timedelta | None = "raise",
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
    dt = pd.to_datetime(values, utc=False, errors="coerce")  # returns Series or DatetimeIndex matching input

    # Always work with a DatetimeIndex for uniform tz operations
    if isinstance(dt, pd.Series):
        dti = pd.DatetimeIndex(dt)
    else:
        dti = dt

    # Preserve original NaT positions prior to localization
    orig_is_nat = pd.isna(dti)

    # Localize / convert only non-NaT subset to avoid warnings
    if orig_is_nat.any():
        working = dti[~orig_is_nat]
    else:
        working = dti

    if working.tz is None:
        if assume_tz:
            working = working.tz_localize(ZoneInfo(assume_tz), ambiguous=ambiguous, nonexistent=nonexistent)
        else:
            working = working.tz_localize("UTC")
    dt_utc = working.tz_convert("UTC")

    # Reconstruct full aligned array with NaT where applicable
    if orig_is_nat.any():
        # create empty tz-aware index to align
        rebuilt = []
        j = 0
        for is_na in orig_is_nat:
            if is_na:
                rebuilt.append(pd.NaT)
            else:
                rebuilt.append(dt_utc[j])
                j += 1
        dt_utc_full = pd.DatetimeIndex(rebuilt)
    else:
        dt_utc_full = dt_utc

    # Vectorized epoch ms
    epoch_ms_array = (dt_utc_full.view("int64") // 1_000_000)
    out = pd.Series(epoch_ms_array, index=orig_index, name=getattr(values, "name", None))
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

from __future__ import annotations

from typing import Protocol

import pandas as pd

REQUIRED_CANDLE_COLUMNS = ["ts", "open", "high", "low", "close", "volume"]


class CandleProvider(Protocol):  # pragma: no cover - structural
    def __call__(self, symbol: str, *, start: int | None = None, end: int | None = None, **kwargs: object) -> pd.DataFrame: ...


def validate_candles(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in REQUIRED_CANDLE_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing candle columns: {missing}")
    # Sort by ts ascending
    df = df.sort_values("ts", kind="mergesort").reset_index(drop=True)
    # Enforce monotonic strictly increasing
    ts = df["ts"].to_numpy()
    if pd.isna(ts).any():
        raise ValueError("Timestamp column contains NaN")
    if (ts[1:] <= ts[:-1]).any():
        raise ValueError("Timestamps must be strictly increasing")
    return df


__all__ = ["REQUIRED_CANDLE_COLUMNS", "CandleProvider", "validate_candles"]

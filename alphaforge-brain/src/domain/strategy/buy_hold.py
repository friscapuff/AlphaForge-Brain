from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from .base import strategy


@strategy("buy_hold")
def buy_hold_signals(
    df: pd.DataFrame, params: Dict[str, Any] | None = None
) -> pd.DataFrame:
    """Minimal buy & hold strategy producing continuous long signal.

    Requirements downstream (risk + simulator) expect columns:
      ['timestamp','open','high','low','close','volume','signal']
    We forward price columns from input (assuming input already contains canonical candle fields) and
    emit a constant +1 signal series.
    """
    if df is None or len(df) == 0:
        return pd.DataFrame(
            columns=["timestamp", "open", "high", "low", "close", "volume", "signal"]
        )
    out = pd.DataFrame(index=df.index.copy())
    # Forward required OHLCV columns if present else synthesize benign defaults
    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns:
            out[col] = df[col].astype("float64")
        else:
            if col == "volume":
                out[col] = 0
            else:
                # Use close or open fallback to keep monotonic structure
                base = df.get("close") or df.get("open")
                if base is not None:
                    out[col] = base.astype("float64")
                else:
                    out[col] = 100.0
    # Timestamp column (epoch ms) if original has 'ts'
    if "ts" in df.columns:
        out["timestamp"] = df["ts"].values
    else:
        # Create synthetic epoch sequence
        out["timestamp"] = range(len(out))
    out["signal"] = 1
    return out.reset_index(drop=True)


__all__ = ["buy_hold_signals"]

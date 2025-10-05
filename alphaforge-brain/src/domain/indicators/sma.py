from __future__ import annotations

import pandas as pd

from .registry import IndicatorProtocol, indicator, indicator_registry


class SimpleMovingAverage(IndicatorProtocol):
    """Single-window simple moving average indicator producing a single feature column.

    Feature column naming convention used by feature engine tests: SMA_{window}_close
    """

    def __init__(self, window: int) -> None:
        if window < 1:
            raise ValueError("window must be >= 1")
        self.window = int(window)
        self.name = "SMA"

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        if "close" not in df.columns:
            raise ValueError("DataFrame must contain 'close' column")
        out = pd.DataFrame(index=df.index)
        out[self.feature_columns()[0]] = (
            df["close"].rolling(window=self.window, min_periods=self.window).mean()
        )
        return out

    def feature_columns(self) -> list[str]:
        return [f"SMA_{self.window}_close"]


__all__ = ["SimpleMovingAverage", "indicator_registry"]


@indicator("dual_sma")
def dual_sma_indicator(
    df: pd.DataFrame, params: dict[str, int] | None = None
) -> pd.DataFrame:  # legacy wrapper for tests
    """Legacy dual SMA producing short & long windows in a single call.

    Maintains previous API used by tests expecting columns:
      sma_short_<short_window>, sma_long_<long_window>
    """

    if params is None:
        params = {}
    short_w = int(params.get("short_window", 10))
    long_w = int(params.get("long_window", 50))
    if short_w < 1:
        raise ValueError("short_window must be >= 1")
    if long_w <= short_w:
        raise ValueError("long_window must be > short_window")
    if "close" not in df.columns:
        raise ValueError("DataFrame must contain 'close' column")
    out = df.copy()
    out[f"sma_short_{short_w}"] = (
        out["close"].rolling(window=short_w, min_periods=short_w).mean()
    )
    out[f"sma_long_{long_w}"] = (
        out["close"].rolling(window=long_w, min_periods=long_w).mean()
    )
    return out


__all__.append("dual_sma_indicator")

"""Type-friendly features cache shim.

Defines a minimal protocol that matches the expected interface. No dynamic
rebinding is performed to keep mypy satisfied.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Callable, Protocol, runtime_checkable

import pandas as pd


@runtime_checkable
class FeaturesCache(Protocol):
    def __init__(self, root: Path) -> None: ...

    def load_or_build(
        self,
        candle_df: pd.DataFrame,
        indicators: Iterable[object],
        build_fn: Callable[[pd.DataFrame], pd.DataFrame],
        *,
        candle_hash: str,
        engine_version: str,
    ) -> pd.DataFrame: ...


__all__ = ["FeaturesCache"]

from __future__ import annotations

"""DataSource abstraction (Phase J G02).

Provides a protocol-style base and concrete LocalCsvDataSource implementation that
will be wired into the dataset registry in G03 and orchestrator integration in G05.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable, Any

import pandas as pd

from domain.data.ingest_nvda import load_canonical_dataset, slice_canonical, DatasetMetadata


@runtime_checkable
class DataSource(Protocol):  # pragma: no cover - interface only
    symbol: str
    timeframe: str

    def load(self) -> tuple[pd.DataFrame, DatasetMetadata]:
        """Load (and possibly cache) the full canonical dataset for this (symbol,timeframe)."""

    def slice(self, start_ms: int | None, end_ms: int | None) -> pd.DataFrame:
        """Return a sliced view (copy) of the canonical dataset within inclusive ms bounds."""


@dataclass(slots=True)
class LocalCsvDataSource:
    symbol: str
    timeframe: str
    root: Path = Path("data")
    # For NVDA transitional reuse we delegate to existing NVDA ingestion; future refactor (G04) removes symbol coupling.

    def load(self) -> tuple[pd.DataFrame, DatasetMetadata]:
        if self.symbol.upper() != "NVDA":  # pragma: no cover - defensive until G04 generic ingestion
            raise NotImplementedError("Only NVDA supported in transitional LocalCsvDataSource (pre-G04 refactor).")
        return load_canonical_dataset(self.root)

    def slice(self, start_ms: int | None, end_ms: int | None) -> pd.DataFrame:
        if self.symbol.upper() != "NVDA":  # pragma: no cover
            raise NotImplementedError("Only NVDA supported in transitional LocalCsvDataSource (pre-G04 refactor).")
        return slice_canonical(start_ms, end_ms)


__all__ = [
    "DataSource",
    "LocalCsvDataSource",
    # Future provider stubs
]


class ApiDataSource:  # pragma: no cover - stub
    """Placeholder for future external API sourced historical data.

    Phase J (G08): non-functional stub enabling early registry wiring & contract planning.
    """

    def __init__(self, symbol: str, timeframe: str, base_url: str) -> None:
        self.symbol = symbol
        self.timeframe = timeframe
        self.base_url = base_url

    def load(self):  # type: ignore[override]
        raise NotImplementedError("ApiDataSource load not implemented (stub)")

    def slice(self, start_ms: int | None, end_ms: int | None):  # type: ignore[override]
        raise NotImplementedError("ApiDataSource slice not implemented (stub)")


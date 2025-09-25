from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Callable

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from infra.utils.hash import sha256_of_text


def _hash_indicators(indicators: Iterable[object]) -> str:
    # Mirror test _indicator_signature: name + optional window using colon separator
    parts: list[str] = []
    for ind in indicators:
        name = getattr(ind, "name", ind.__class__.__name__)
        window = getattr(ind, "window", None)
        sig = name
        if isinstance(window, int):
            sig += f":window={window}"
        parts.append(sig)
    key = "|".join(sorted(parts))
    digest: str = sha256_of_text(key)
    return digest[:16]


class FeaturesCache:
    """Filesystem cache for computed feature DataFrames.

    Cache key components provided by caller:
      - candle_hash: surrogate for underlying candle frame content
      - indicators: iterable of indicator objects (affects key via deterministic signature)
      - engine_version: version string for invalidation on engine logic changes
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(
        self, candle_hash: str, indicators: Iterable[object], engine_version: str
    ) -> Path:
        # Build expected digest: sha256( sorted_indicator_signatures_joined + '|' + engine_version )[:16]
        # Reconstruct the full signatures (not truncated) to match test logic
        parts: list[str] = []
        for ind in indicators:
            name = getattr(ind, "name", ind.__class__.__name__)
            window = getattr(ind, "window", None)
            sig = name
            if isinstance(window, int):
                sig += f":window={window}"
            parts.append(sig)
        sigs_joined = "|".join(sorted(parts))
        digest16 = sha256_of_text(sigs_joined + "|" + engine_version)[:16]
        composite = f"{candle_hash}_{digest16}"
        return self.root / f"{composite}.parquet"

    def load_or_build(
        self,
        candle_df: pd.DataFrame,
        indicators: Iterable[object],
        build_fn: Callable[[pd.DataFrame], pd.DataFrame],
        *,
        candle_hash: str,
        engine_version: str,
    ) -> pd.DataFrame:
        path = self._path(candle_hash, indicators, engine_version)
        if path.exists():
            try:
                return self._read(path)
            except Exception:  # corrupted -> rebuild
                try:
                    path.unlink()
                except FileNotFoundError:  # pragma: no cover - race
                    pass
        df = build_fn(candle_df)
        self._write(path, df)
        return df

    def _write(self, path: Path, df: pd.DataFrame) -> None:
        table = pa.Table.from_pandas(df)
        pq.write_table(table, path)

    def _read(self, path: Path) -> pd.DataFrame:
        table = pq.read_table(path)
        df = table.to_pandas()
        assert isinstance(df, pd.DataFrame)
        return df


__all__ = ["FeaturesCache"]

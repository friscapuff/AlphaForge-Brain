from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .. import registry as data_registry
from .base import REQUIRED_CANDLE_COLUMNS, validate_candles


@data_registry.provider("local")
def load_local(
    *,
    symbol: str,
    path: str,
    start: int | None = None,
    end: int | None = None,
    recursive: bool = False,
    allow_parquet: bool = True,
    allow_csv: bool = True,
    **_: Any,
) -> pd.DataFrame:
    """Load candle data from a file or directory of CSV/Parquet files.

    Parameters
    ----------
    symbol : str
        Symbol identifier (currently unused, placeholder for future filtering).
    path : str
        File or directory path.
    start, end : int | None
        Optional inclusive epoch (or integer) boundaries to filter on `ts`.
    recursive : bool
        Whether to recurse into subdirectories when path is a directory.
    allow_parquet / allow_csv : bool
        Enable corresponding file type ingestion.

    Returns
    -------
    DataFrame with REQUIRED_CANDLE_COLUMNS strictly increasing in `ts`.
    """
    root = Path(path)
    if not root.exists():  # pragma: no cover - defensive
        raise FileNotFoundError(path)

    files: list[Path] = []
    if root.is_file():
        files = [root]
    else:
        glob_pattern = "**/*" if recursive else "*"
        for f in root.glob(glob_pattern):
            if f.is_dir():
                continue
            if allow_csv and f.suffix.lower() == ".csv":
                files.append(f)
            elif allow_parquet and f.suffix.lower() in {".parquet", ".pq"}:
                files.append(f)

    # Deterministic ordering of ingestion by file name
    files.sort(key=lambda p: p.name)
    if not files:
        raise ValueError(f"No data files found at {path}")

    frames: list[pd.DataFrame] = []
    for f in files:
        if f.suffix.lower() == ".csv":
            df = pd.read_csv(f)
        else:
            df = pd.read_parquet(f)
        frames.append(df)

    combined = pd.concat(frames, ignore_index=True)

    # Filter by start/end if provided
    if start is not None:
        combined = combined[combined["ts"] >= start]
    if end is not None:
        combined = combined[combined["ts"] <= end]

    # Keep only required + any extra columns (validate will ensure required present & ordering)
    combined = validate_candles(combined)

    # Reorder columns: required first then extras (stable)
    extras = [c for c in combined.columns if c not in REQUIRED_CANDLE_COLUMNS]
    ordered_cols = REQUIRED_CANDLE_COLUMNS + extras
    return combined[ordered_cols]


__all__ = ["load_local"]

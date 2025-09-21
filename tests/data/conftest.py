import os
import pytest
import pandas as pd

from pathlib import Path

from domain.data.ingest_nvda import load_canonical_dataset, slice_canonical, SYMBOL


@pytest.fixture(scope="session")
def nvda_canonical():
    """Session-scoped canonical NVDA dataset (loads once). Skips if CSV missing."""
    csv_primary = Path("data") / "NVDA_5y.csv"
    csv_alt = Path("src") / "domain" / "data" / "NVDA_5y.csv"
    use_alt = not csv_primary.exists() and csv_alt.exists()
    csv_path = csv_primary if not use_alt else csv_alt
    assert csv_path.exists(), "Expected NVDA_5y.csv in data/ or src/domain/data/; add dataset before running tests"
    # If using alternate location, pass its parent as data_dir so loader finds file
    data_dir = csv_path.parent if use_alt else None
    df, meta = load_canonical_dataset(data_dir=data_dir)
    return df, meta


@pytest.fixture(scope="function")
def nvda_canonical_slice(nvda_canonical):
    df, meta = nvda_canonical
    # Take a deterministic middle slice (avoid edges for moving averages)
    assert len(df) >= 120, f"Dataset unexpectedly small (<120 rows); got {len(df)} rows from {Path('data')/'NVDA_5y.csv' if (Path('data')/'NVDA_5y.csv').exists() else (Path('src')/'domain'/'data'/'NVDA_5y.csv')}"
    mid_start = int(df.iloc[len(df)//3]["ts"])
    mid_end = int(df.iloc[len(df)//3 + 100]["ts"]) if len(df) > (len(df)//3 + 100) else int(df.iloc[-1]["ts"])
    sliced = slice_canonical(mid_start, mid_end)
    return sliced, meta

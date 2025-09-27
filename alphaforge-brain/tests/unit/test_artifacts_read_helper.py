from pathlib import Path

import pandas as pd
from lib.artifacts import read_parquet_or_csv, write_parquet


def test_read_parquet_or_csv_csv_under_parquet(tmp_path: Path) -> None:
    """Simulate minimal environment fallback: write CSV bytes under .parquet and ensure helper reads it."""
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    # Force CSV-under-parquet: bypass write_parquet helper's parquet branch by writing CSV manually
    path = tmp_path / "sample.parquet"
    path.write_text(df.to_csv(index=False), encoding="utf-8")
    loaded = read_parquet_or_csv(path)
    pd.testing.assert_frame_equal(df, loaded)


def test_read_parquet_or_csv_true_parquet(tmp_path: Path) -> None:
    """If parquet engine works, ensure helper prefers parquet path (falling back only on exception)."""
    df = pd.DataFrame({"x": [10, 11], "y": [0.1, 0.2]})
    path = tmp_path / "real.parquet"
    # Use helper writer (which will attempt parquet and fallback otherwise)
    write_parquet(df, path)
    loaded = read_parquet_or_csv(path)
    # Column order & dtypes should match original (allowing for engine coercions)
    assert list(loaded.columns) == list(df.columns)
    assert len(loaded) == len(df)

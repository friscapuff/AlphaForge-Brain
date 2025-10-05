from __future__ import annotations

import pandas as pd
from src.services.chunking import choose_chunk_size, estimate_row_size_bytes_from_df


def test_estimate_row_size_simple_numeric():
    df = pd.DataFrame(
        {
            "a": pd.Series([1], dtype="int64"),
            "b": pd.Series([1.0], dtype="float64"),
            "c": pd.Series([True], dtype="bool"),
            "d": pd.to_datetime(["2024-01-01"]),
        }
    )
    est = estimate_row_size_bytes_from_df(df)
    # 8 + 8 + 1 + 8 = 25 bytes
    assert est >= 25


def test_choose_chunk_size_respects_budget_and_cap():
    df = pd.DataFrame(
        {
            "a": pd.Series([1], dtype="int64"),
            "b": pd.Series([1.0], dtype="float64"),
        }
    )
    # row ~ 16 bytes -> 1 MB budget -> ~65536 rows, capped by cap
    rows = choose_chunk_size(df, target_chunk_mb=1, max_rows_cap=1000000)
    assert 60000 <= rows <= 70000

    # Very small cap should be respected
    rows2 = choose_chunk_size(df, target_chunk_mb=100, max_rows_cap=1000)
    assert rows2 == 1000

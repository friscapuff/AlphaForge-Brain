"""T031: Unexpected gap detection test.

Creates a temporary CSV with a deliberate missing business day and ensures
generic ingestion counts at least one unexpected gap.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from domain.data.ingest_csv import load_generic_csv


def test_gap_detection_counts_missing_session(tmp_path: Path) -> None:
    ts_all = pd.date_range("2024-01-01", periods=3, freq="1D")
    # Remove middle day to create a gap
    keep = [0, 2]
    df = pd.DataFrame(
        {
            "timestamp": [ts_all[i].isoformat() for i in keep],
            "open": [1, 3],
            "high": [1, 3],
            "low": [1, 3],
            "close": [1, 3],
            "volume": [100, 120],
        }
    )
    csv_path = tmp_path / "GAPTEST.csv"
    df.to_csv(csv_path, index=False)

    # Ingest with calendar id NASDAQ
    _, meta = load_generic_csv("GAP", "1d", csv_path, "NASDAQ")
    assert (
        meta.anomaly_counters["unexpected_gaps"] >= 1
    ), "Missing session not detected as unexpected gap"

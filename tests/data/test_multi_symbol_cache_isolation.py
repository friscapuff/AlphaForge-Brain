from __future__ import annotations

import pandas as pd
from pathlib import Path
import tempfile

from domain.data.registry import register_dataset, DatasetEntry
from domain.data.datasource import LocalCsvDataSource


def _write_csv(path: Path, start_price: float) -> None:
    rows = []
    price = start_price
    for i in range(5):
        price += 1
        rows.append({
            "timestamp": f"2024-01-0{i+1}",
            "open": price,
            "high": price + 0.5,
            "low": price - 0.5,
            "close": price + 0.2,
            "volume": 1000 + i,
        })
    pd.DataFrame(rows).to_csv(path, index=False)


def test_multi_symbol_cache_isolation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        a_path = tmp_path / "AAA.csv"
        b_path = tmp_path / "BBB.csv"
        _write_csv(a_path, 10)
        _write_csv(b_path, 200)

        register_dataset(DatasetEntry(symbol="AAA", timeframe="1d", provider="local_csv", path=str(a_path), calendar_id=None))
        register_dataset(DatasetEntry(symbol="BBB", timeframe="1d", provider="local_csv", path=str(b_path), calendar_id=None))

        src_a = LocalCsvDataSource("AAA", "1d", root=tmp_path)
        src_b = LocalCsvDataSource("BBB", "1d", root=tmp_path)

        frame_a, meta_a = src_a.load()
        frame_b, meta_b = src_b.load()

        assert meta_a.symbol == "AAA" and meta_b.symbol == "BBB"
        assert meta_a.data_hash != meta_b.data_hash  # distinct content => distinct hashes
        slice_a = src_a.slice(frame_a["ts"].iloc[1], frame_a["ts"].iloc[3])
        slice_b = src_b.slice(frame_b["ts"].iloc[1], frame_b["ts"].iloc[3])
        assert len(slice_a) == 3
        assert len(slice_b) == 3
        # Ensure slices correspond to correct symbols by comparing first close value relation
        assert slice_a.loc[0, "close"] < slice_b.loc[0, "close"]
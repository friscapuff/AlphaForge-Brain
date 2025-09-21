
from pathlib import Path

import domain.data.providers.local  # noqa: F401  # trigger registration
from domain.data import registry as data_registry
from domain.data.providers.base import REQUIRED_CANDLE_COLUMNS, validate_candles


def test_local_provider_csv_loading(tmp_path: Path) -> None:
    csv_content = "ts,open,high,low,close,volume\n1,10,11,9,10.5,100\n2,10.5,11.5,10,11,150\n3,11,12,10.5,11.5,120\n"
    p = tmp_path / "sample.csv"
    p.write_text(csv_content)

    loader = data_registry.ProviderRegistry.get("local")
    df = loader(symbol="TEST", path=str(p))
    assert list(df.columns) == REQUIRED_CANDLE_COLUMNS
    assert df.shape[0] == 3
    assert df.ts.is_monotonic_increasing
    validate_candles(df)  # should not raise


def test_local_provider_deterministic_ordering(tmp_path: Path) -> None:
    # Two CSV files out of order; provider should concatenate & sort
    csv1 = "ts,open,high,low,close,volume\n2,10.5,11.5,10,11,150\n3,11,12,10.5,11.5,120\n"
    csv2 = "ts,open,high,low,close,volume\n1,10,11,9,10.5,100\n"
    p1 = tmp_path / "b.csv"
    p2 = tmp_path / "a.csv"
    p1.write_text(csv1)
    p2.write_text(csv2)

    loader = data_registry.ProviderRegistry.get("local")
    df = loader(symbol="TEST", path=str(tmp_path))
    assert list(df.ts) == [1,2,3]
    assert df.index.tolist() == [0,1,2]
    validate_candles(df)

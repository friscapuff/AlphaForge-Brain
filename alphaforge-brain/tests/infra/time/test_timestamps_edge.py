from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest
from zoneinfo import ZoneInfo

from infra.time.timestamps import to_epoch_ms

# Using US/Eastern for DST transitions (2023-03-12 02:00 jump forward, 2023-11-05 01:00 repeat)
EASTERN = "US/Eastern"


def test_naive_interpreted_as_utc() -> None:
    ts = pd.Series(["2024-01-01 00:00:00"])  # naive
    out = to_epoch_ms(ts)
    assert out.dtype == "int64" or str(out.dtype) == "Int64"
    # Convert manual
    expected = int(pd.Timestamp("2024-01-01T00:00:00Z").value // 1_000_000)
    assert out.iloc[0] == expected


def test_naive_with_assume_tz_and_dst_ambiguous_raises() -> None:
    # Ambiguous time (falls back) 2023-11-05 01:30 occurs twice in US/Eastern
    ambiguous_time = pd.Series(["2023-11-05 01:30:00"])  # naive
    try:
        from pandas._libs.tslibs.tzconversion import (
            AmbiguousTimeError,
        )  # pragma: no cover

        exc_type = AmbiguousTimeError
    except Exception:  # pragma: no cover
        exc_type = Exception
    with pytest.raises(exc_type):
        to_epoch_ms(ambiguous_time, assume_tz=EASTERN)  # default ambiguous='raise'


def test_naive_with_assume_tz_and_dst_ambiguous_resolved() -> None:
    ambiguous_time = pd.Series(["2023-11-05 01:30:00"])  # naive
    # Resolve by picking fold=False (first occurrence) via ambiguous=False
    out = to_epoch_ms(ambiguous_time, assume_tz=EASTERN, ambiguous=False)
    assert len(out) == 1


def test_nonexistent_spring_forward_shift_forward() -> None:
    # Non-existent local time 2023-03-12 02:30:00 in US/Eastern
    nonexistent = pd.Series(["2023-03-12 02:30:00"])  # naive
    out = to_epoch_ms(nonexistent, assume_tz=EASTERN, nonexistent="shift_forward")
    assert len(out) == 1


def test_preserve_nat_and_future_clip() -> None:
    future = datetime.now(timezone.utc) + timedelta(days=5)
    series = pd.Series(["2024-01-01 00:00:00", pd.NaT, future])
    out = to_epoch_ms(series, clip_future=True)
    # Future removed, NaT preserved as <NA>
    assert out.isna().sum() == 1
    # Ensure no value > now
    assert (out.dropna() <= int(pd.Timestamp.utcnow().value // 1_000_000)).all()


def test_series_name_preserved() -> None:
    s = pd.Series(["2024-02-01"], name="when")
    out = to_epoch_ms(s)
    assert out.name == "when"


def test_datetimeindex_input_returns_reset_index() -> None:
    idx = pd.DatetimeIndex(["2024-02-01", "2024-02-02"])  # naive
    out = to_epoch_ms(idx)
    # Index should be RangeIndex after reset
    assert list(out.index) == [0, 1]


def test_tz_aware_passthrough() -> None:
    aware = pd.Series([datetime(2024, 1, 1, 12, 0, tzinfo=ZoneInfo("UTC"))])
    out = to_epoch_ms(aware)
    assert out.iloc[0] == int(pd.Timestamp("2024-01-01T12:00:00Z").value // 1_000_000)

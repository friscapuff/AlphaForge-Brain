from __future__ import annotations

import pandas as pd

from infra.time.timestamps import to_epoch_ms


def test_to_epoch_ms_preserves_length_with_assume_tz() -> None:
    # Multi-row naive datetimes that require localization (avoid DST boundary complexity)
    dt_strings = ["2024-09-10 08:30:00", "2024-09-10 09:15:00", "2024-09-10 10:45:00"]
    s = pd.Series(pd.to_datetime(dt_strings))
    out = to_epoch_ms(s, assume_tz="America/New_York")
    assert len(out) == len(s), "Output length mismatch (regression guard)"
    # All should be integers (nullable type accepted) and monotonic increasing
    assert out.notna().all(), "Expected non-null epoch ms values with infer/shift_forward handling"
    assert out.is_monotonic_increasing, "Epoch ms not monotonic increasing"
    # Spot check first conversion against pandas reference
    ref0 = pd.to_datetime(dt_strings[0]).tz_localize("America/New_York").tz_convert("UTC")
    ref0_ms = int(ref0.timestamp() * 1000)
    # Allow exact match
    assert int(out.iloc[0]) == ref0_ms, "Unexpected epoch ms for first element"


def test_to_epoch_ms_empty_series() -> None:
    s = pd.Series([], dtype="datetime64[ns]")
    out = to_epoch_ms(s, assume_tz="America/New_York")
    assert len(out) == 0
    assert str(out.dtype) in {"Int64", "int64"}

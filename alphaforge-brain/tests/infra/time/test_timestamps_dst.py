from __future__ import annotations

import pandas as pd
import pytest

from infra.time.timestamps import to_epoch_ms

# DST fall-back (US/Eastern 2024-11-03) creates ambiguous times between 01:00:00 and 01:59:59
# We assert ambiguous="NaT" path yields NaT values preserving length.


def test_to_epoch_ms_ambiguous_fallback_nat() -> None:
    s = pd.Series(pd.to_datetime(["2024-11-03 01:15:00", "2024-11-03 01:45:00"]))
    out_nat = to_epoch_ms(
        s, assume_tz="America/New_York", ambiguous="NaT", nonexistent="raise"
    )
    assert len(out_nat) == 2
    assert (
        out_nat.isna().all()
    ), "Ambiguous times should map to NaT under ambiguous='NaT'"


def test_to_epoch_ms_nonexistent_spring_forward_shift_forward() -> None:
    # Spring-forward gap (US/Eastern 2024-03-10) 02:00-02:59 local times do not exist
    dt_strings = ["2024-03-10 01:30:00", "2024-03-10 02:15:00", "2024-03-10 03:05:00"]
    s = pd.Series(pd.to_datetime(dt_strings))
    out_shift = to_epoch_ms(
        s, assume_tz="America/New_York", ambiguous="raise", nonexistent="shift_forward"
    )
    assert len(out_shift) == 3
    # Middle value was nonexistent; ensure it is >= first and <= third (shifted forward by pandas)
    assert out_shift.iloc[0] < out_shift.iloc[1] < out_shift.iloc[2]


def test_to_epoch_ms_nonexistent_spring_forward_nat() -> None:
    dt_strings = ["2024-03-10 02:05:00", "2024-03-10 02:30:00"]
    s = pd.Series(pd.to_datetime(dt_strings))
    out_nat = to_epoch_ms(
        s, assume_tz="America/New_York", ambiguous="raise", nonexistent="NaT"
    )
    assert len(out_nat) == 2
    assert (
        out_nat.isna().all()
    ), "Nonexistent times should map to NaT under nonexistent='NaT'"


@pytest.mark.parametrize(
    "ambiguous_strategy", ["NaT", "raise"]
)  # smoke parameterization
def test_to_epoch_ms_ambiguous_parametrized_behavior(ambiguous_strategy: str) -> None:
    s = pd.Series(pd.to_datetime(["2024-11-03 01:05:00"]))
    if ambiguous_strategy == "raise":
        # Ambiguous 01:05 during fallback should raise pandas AmbiguousTimeError
        try:
            from pandas._libs.tslibs.np_datetime import AmbiguousTimeError  # type: ignore
        except Exception:  # pragma: no cover - fallback if internals change
            AmbiguousTimeError = Exception  # type: ignore
        with pytest.raises(AmbiguousTimeError):
            to_epoch_ms(s, assume_tz="America/New_York", ambiguous=ambiguous_strategy)
    else:
        out = to_epoch_ms(s, assume_tz="America/New_York", ambiguous=ambiguous_strategy)
        assert out.isna().all()

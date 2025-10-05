from __future__ import annotations

import pytest
from domain.time.timeframe import parse_timeframe


@pytest.mark.parametrize(
    "raw,canonical,seconds",
    [
        ("1m", "1m", 60),
        ("1min", "1m", 60),
        ("5m", "5m", 5 * 60),
        ("60m", "1h", 3600),
        ("1day", "1d", 86400),
        ("24h", "1d", 86400),
    ],
)
def test_parse_timeframe_aliases(raw: str, canonical: str, seconds: int) -> None:
    spec = parse_timeframe(raw)
    assert spec.canonical == canonical
    assert spec.bar_seconds == seconds


@pytest.mark.parametrize("bad", ["", "2m", "1M", "60s", "7h", "1w"])
def test_parse_timeframe_invalid(bad: str) -> None:
    with pytest.raises(ValueError):
        parse_timeframe(bad)

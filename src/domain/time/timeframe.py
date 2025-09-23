"""Timeframe canonicalization & parsing (Phase K T051).

Provides a single entrypoint `parse_timeframe` that normalizes user supplied
timeframe strings into a canonical spec used for validation & metadata.

Supported canonical forms (string):
    1m,5m,15m,30m,1h,2h,4h,1d

Alias normalization examples:
    1min -> 1m, 01M -> 1m, 60min -> 1h, 1day -> 1d, 24h -> 1d

Returned object: TimeframeSpec (frozen dataclass) with attributes:
    canonical: canonical string (e.g. "1m")
    unit: one of {"m","h","d"}
    length: int length component
    bar_seconds: int (length * unit seconds)
    label: human friendly label (e.g. "1 Minute")

Raises ValueError on unsupported timeframe.
"""

from __future__ import annotations

from dataclasses import dataclass

_UNIT_SECONDS = {"m": 60, "h": 3600, "d": 86400}

_CANONICAL: dict[str, tuple[int, str]] = {
    "1m": (1, "m"),
    "5m": (5, "m"),
    "15m": (15, "m"),
    "30m": (30, "m"),
    "1h": (1, "h"),
    "2h": (2, "h"),
    "4h": (4, "h"),
    "1d": (1, "d"),
}

_ALIASES: dict[str, str] = {
    "1min": "1m",
    "01m": "1m",
    "60m": "1h",
    "60min": "1h",
    "120m": "2h",
    "240m": "4h",
    "1day": "1d",
    "24h": "1d",
    "1440m": "1d",
}


@dataclass(frozen=True, slots=True)
class TimeframeSpec:
    canonical: str
    unit: str
    length: int
    bar_seconds: int
    label: str


def parse_timeframe(raw: str) -> TimeframeSpec:
    if not raw:
        raise ValueError("timeframe required")
    s = raw.strip()
    s = _ALIASES.get(s, s)  # alias normalize
    if s not in _CANONICAL:
        raise ValueError(f"Unsupported timeframe '{raw}' (normalized '{s}')")
    length, unit = _CANONICAL[s]
    bar_seconds = length * _UNIT_SECONDS[unit]
    unit_label = {"m": "Minute", "h": "Hour", "d": "Day"}[unit]
    label = f"{length} {unit_label if length==1 else unit_label + 's'}"
    return TimeframeSpec(canonical=s, unit=unit, length=length, bar_seconds=bar_seconds, label=label)


__all__ = ["TimeframeSpec", "parse_timeframe"]

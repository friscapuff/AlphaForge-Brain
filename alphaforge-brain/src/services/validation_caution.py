"""Compute validation caution flag (Phase 4).

T040 - Compute Caution Flag

Logic:
  - Load threshold & optional metric filter from settings.validation_caution
  - Inspect provided p-values mapping (metric_key -> float)
  - Select only metrics in filter (if filter non-empty)
  - Collect metrics with p < threshold (strictly less)
  - Return (flag: bool, metrics: list[str])

If threshold <= 0 or no metrics provided -> (False, [])

Intentionally pure & deterministic for hashing isolation; output does not affect run hash yet.
"""

from __future__ import annotations

from typing import Mapping

from settings.validation_caution import load_caution_settings


def compute_caution(p_values: Mapping[str, float] | None) -> tuple[bool, list[str]]:
    settings = load_caution_settings()
    if settings.threshold <= 0:
        return False, []
    if not p_values:
        return False, []
    items = []
    for k, v in p_values.items():
        if not isinstance(v, (int, float)):
            continue
        if settings.metric_filter and k not in settings.metric_filter:
            continue
        try:
            fv = float(v)
        except Exception:  # pragma: no cover
            continue
        if fv < settings.threshold:
            items.append(k)
    items.sort()
    return (len(items) > 0, items)


__all__ = ["compute_caution"]

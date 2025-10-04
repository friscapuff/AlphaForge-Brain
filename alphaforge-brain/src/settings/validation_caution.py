"""Validation caution threshold settings (Phase 4 scaffolding).

T040 - Compute Caution Flag

Environment Variables:
  AF_VALIDATION_CAUTION_PVALUE   Float in (0,1]; p-value threshold below which validation_caution=True
  AF_VALIDATION_CAUTION_METRICS  Comma-separated allowed metric keys to inspect (optional filter)

Defaults:
  threshold = 0.0 (disabled) until explicitly set (>0 & <=1)
  metrics filter = unset (inspect all provided p-values)

Usage:
  from settings.validation_caution import load_caution_settings
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class CautionSettings:
    threshold: float  # <=0 disables
    metric_filter: tuple[str, ...]  # empty -> all


def _parse_threshold() -> float:
    raw = os.getenv("AF_VALIDATION_CAUTION_PVALUE")
    if not raw:
        return 0.0
    try:
        v = float(raw)
    except ValueError:
        return 0.0
    if v <= 0 or v > 1:
        return 0.0
    return v


def _parse_metrics_filter() -> tuple[str, ...]:
    raw = os.getenv("AF_VALIDATION_CAUTION_METRICS")
    if not raw:
        return tuple()
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return tuple(sorted(set(parts)))


@lru_cache(maxsize=1)
def load_caution_settings() -> CautionSettings:
    return CautionSettings(
        threshold=_parse_threshold(), metric_filter=_parse_metrics_filter()
    )


__all__ = ["load_caution_settings", "CautionSettings"]

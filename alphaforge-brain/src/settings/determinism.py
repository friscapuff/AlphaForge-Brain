"""Determinism & numerical tolerance settings.

T010 - Determinism Settings Module (FR references: Equity normalization & hash stability)

Centralizes small floating point tolerances used in hash-sensitive computations
(e.g., drawdown epsilon). Exposes environment overrides for experimentation
without requiring code changes, while keeping defaults stable for CI.

Environment Variables:
  AF_DRAWNDOWN_EPSILON   Float > 0; tolerance when comparing expected vs computed drawdown

Usage:
  from settings.determinism import DRAWNDOWN_EPSILON

Rationale:
  A single source of truth prevents silent drift if multiple modules each embed
  their own tolerance values. The variable is deliberately *not* named with a
  generic prefix to avoid unintentional collision.
"""

from __future__ import annotations

import os
from functools import lru_cache


def _parse_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        val = float(raw)
    except ValueError:
        return default
    if val <= 0:
        return default
    return val


@lru_cache(maxsize=1)
def _load() -> float:
    # Default chosen to balance strictness vs FP noise; revisit if normalization changes.
    return _parse_float("AF_DRAWNDOWN_EPSILON", 1e-9)


DRAWNDOWN_EPSILON: float = _load()

__all__ = ["DRAWNDOWN_EPSILON"]

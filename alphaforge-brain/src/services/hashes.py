"""Consolidated hashing interfaces (T020).

Provides stable signatures wrapping legacy implementations so callers can migrate
without hash drift.

Exports:
  - metrics_signature(metrics: Mapping[str, Any]) -> str
  - equity_signature(curve: Sequence[Any] | pandas.DataFrame) -> str

Implementation delegates to existing services.metrics_hash to guarantee bit-for-bit
parity during Phase 2. Deprecation shims will later forward old names here (T022).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd
from services.metrics_hash import equity_curve_hash as _legacy_equity_curve_hash

# Re-use existing proven functions
from services.metrics_hash import metrics_hash as _legacy_metrics_hash

from infra.utils.hash import hash_canonical


def metrics_signature(metrics: Mapping[str, Any]) -> str:  # FR-015 stability
    return _legacy_metrics_hash(metrics)


def equity_signature(curve: Sequence[Any] | pd.DataFrame) -> str:  # FR-015 stability
    return _legacy_equity_curve_hash(curve)


def trust_gate_signature(summary: Mapping[str, Any]) -> str:
    """Deterministically hash trust gate summary payloads."""

    return hash_canonical(summary)


__all__ = ["equity_signature", "metrics_signature", "trust_gate_signature"]

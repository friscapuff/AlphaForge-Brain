"""Metrics core façade (T021).

Wraps domain.metrics.calculator functions to establish stable indirection layer
for future consolidation without changing outputs.

Usage: import services.metrics_core as metrics_core

Guarantees:
 - build_equity_curve and compute_metrics signatures unchanged
 - Pass-through semantics for Phase 2 (hash consolidation) to avoid drift
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from domain.metrics.calculator import build_equity_curve as _build_equity_curve
from domain.metrics.calculator import compute_metrics as _compute_metrics

__all__ = ["build_equity_curve", "compute_metrics"]


def build_equity_curve(positions_df: pd.DataFrame) -> pd.DataFrame:  # FR-015 stability
    return _build_equity_curve(positions_df)


def compute_metrics(
    trades_df: pd.DataFrame,
    equity_curve: pd.DataFrame,
    *,
    include_anomalies: bool = False,
) -> dict[str, Any]:  # FR-015 stability
    return _compute_metrics(
        trades_df, equity_curve, include_anomalies=include_anomalies
    )

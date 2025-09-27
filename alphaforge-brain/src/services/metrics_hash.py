from __future__ import annotations

"""Deterministic hashing utilities for metrics & equity curves.

Provides stable canonical hashing for:
 - metrics_hash(metrics: dict[str, float|int]) -> str
 - equity_curve_hash(bars: Sequence[EquityBar]|pd.DataFrame) -> str

Normalization rules:
 - Only primitive numeric types (float/int) retained for metrics; others coerced via str.
 - Keys sorted; values rounded to 12 significant digits (align canonical_float_precision) before hashing.
 - Equity curve hashed over ordered sequence of (index, nav, drawdown?) where available.
"""

import math
from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd

from infra.config import get_settings
from infra.utils.hash import hash_canonical

try:  # optional runtime import (avoid circular during partial builds)
    from models.equity_bar import EquityBar  # type: ignore
except Exception:  # pragma: no cover - fallback if model not yet importable
    EquityBar = Any  # type: ignore


def _round_sig(x: float, sig: int) -> float:
    if x == 0 or not math.isfinite(x):
        return float(x)
    return float(f"{x:.{sig}g}")


def metrics_hash(metrics: Mapping[str, Any]) -> str:
    settings = get_settings()
    norm: dict[str, Any] = {}
    for k, v in sorted(metrics.items()):
        if isinstance(v, (int, float)):
            norm[k] = _round_sig(float(v), settings.canonical_float_precision)
        else:
            norm[k] = str(v)
    return hash_canonical(norm)


def equity_curve_hash(curve: Sequence[Any]) -> str:
    settings = get_settings()
    rows: list[tuple[int, float, float]] = []
    # Support list[EquityBar], DataFrame with 'nav'/'drawdown', or sequence of dicts
    if isinstance(curve, pd.DataFrame):
        it = enumerate(zip(curve.get("nav", []), curve.get("drawdown", [])))
        for idx, (nav, dd) in it:
            rows.append(
                (
                    idx,
                    _round_sig(float(nav), settings.canonical_float_precision),
                    _round_sig(float(dd), settings.canonical_float_precision),
                )
            )
    else:
        for idx, item in enumerate(curve):
            try:
                nav = float(item.nav)  # type: ignore[arg-type]
                dd = float(getattr(item, "drawdown", 0.0))
            except Exception:  # pragma: no cover
                try:
                    nav = float(item["nav"])  # type: ignore[index]
                    dd = float(item.get("drawdown", 0.0))  # type: ignore[index]
                except Exception:
                    continue
            rows.append(
                (
                    idx,
                    _round_sig(nav, settings.canonical_float_precision),
                    _round_sig(dd, settings.canonical_float_precision),
                )
            )
    payload = {"curve": rows}
    return hash_canonical(payload)


__all__ = ["metrics_hash", "equity_curve_hash"]

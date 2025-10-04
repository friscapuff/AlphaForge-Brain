"""Deterministic hashing utilities for metrics & equity curves.

Provides stable canonical hashing for:
 - metrics_hash(metrics: dict[str, float|int]) -> str
 - equity_curve_hash(curve: Sequence[EquityBar] | pd.DataFrame) -> str

Normalization rules:
 - Only primitive numeric types (float/int) retained for metrics; others coerced via str.
 - Keys sorted; values rounded to 12 significant digits (align canonical_float_precision) before hashing.
 - Equity curve hashed over ordered sequence of (index, nav, drawdown?) where available.
"""

from __future__ import annotations

import math
import warnings
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any

import pandas as pd

from infra.config import get_settings
from infra.utils.hash import hash_canonical

# T022 Deprecation Shims: Forward callers toward services.hashes.* interfaces.
# Keeping original implementation for parity; emit a PendingDeprecationWarning once per process.
_DEPRECATION_EMITTED = False

if TYPE_CHECKING:  # only for static typing; avoid runtime circular import issues
    from models.equity_bar import EquityBar  # pragma: no cover
else:  # runtime lightweight stub (attributes accessed reflectively)

    class EquityBar:  # pragma: no cover
        nav: float  # type: ignore[assignment]
        drawdown: float | None  # type: ignore[assignment]


def _round_sig(x: float, sig: int) -> float:
    if x == 0 or not math.isfinite(x):
        return float(x)
    return float(f"{x:.{sig}g}")


def metrics_hash(metrics: Mapping[str, Any]) -> str:
    global _DEPRECATION_EMITTED
    if not _DEPRECATION_EMITTED:
        warnings.warn(
            "metrics_hash is deprecated; use services.hashes.metrics_signature",
            PendingDeprecationWarning,
            stacklevel=2,
        )
        _DEPRECATION_EMITTED = True
    settings = get_settings()
    norm: dict[str, Any] = {}
    for k, v in sorted(metrics.items()):
        if isinstance(v, (int, float)):
            norm[k] = _round_sig(float(v), settings.canonical_float_precision)
        else:
            norm[k] = str(v)
    return hash_canonical(norm)


def equity_curve_hash(curve: Sequence[Any] | pd.DataFrame) -> str:
    global _DEPRECATION_EMITTED
    if not _DEPRECATION_EMITTED:
        warnings.warn(
            "equity_curve_hash is deprecated; use services.hashes.equity_signature",
            PendingDeprecationWarning,
            stacklevel=2,
        )
        _DEPRECATION_EMITTED = True
    """Return canonical hash for an equity curve.

    Accepts:
      - pandas DataFrame with 'nav' and optional 'drawdown' columns
      - Sequence of EquityBar-like objects (attributes: nav, optional drawdown)
      - Sequence of mappings/dicts with 'nav' and optional 'drawdown' keys
    Missing drawdown values default to 0.0.
    """
    settings = get_settings()
    rows: list[tuple[int, float, float]] = []
    if isinstance(curve, pd.DataFrame):
        nav_series = curve.get("nav")
        dd_series = curve.get("drawdown")
        if nav_series is not None:
            for idx, nav in enumerate(nav_series):
                dd_val = 0.0
                if dd_series is not None and idx < len(dd_series):
                    try:
                        dd_val = float(dd_series.iloc[idx])
                    except Exception:  # pragma: no cover - defensive
                        dd_val = 0.0
                rows.append(
                    (
                        idx,
                        _round_sig(float(nav), settings.canonical_float_precision),
                        _round_sig(float(dd_val), settings.canonical_float_precision),
                    )
                )
    else:
        for idx, item in enumerate(curve):
            # Try attribute style first
            try:
                # Attribute style access
                nav_val = float(item.nav)
                dd_raw = getattr(item, "drawdown", 0.0)
                dd_val = float(dd_raw) if dd_raw is not None else 0.0
            except Exception:
                # Fallback mapping style
                try:
                    nav_val = float(item["nav"])  # mapping style
                    dd_raw = item.get("drawdown", 0.0)
                    dd_val = float(dd_raw) if dd_raw is not None else 0.0
                except Exception:
                    continue
            rows.append(
                (
                    idx,
                    _round_sig(nav_val, settings.canonical_float_precision),
                    _round_sig(dd_val, settings.canonical_float_precision),
                )
            )
    return hash_canonical({"curve": rows})


__all__ = ["equity_curve_hash", "metrics_hash"]

"""Equity normalization utilities (T030)

Removes legacy NAV scaling (e.g. *1_000_000*) while allowing dual-run compare mode
for regression and safety validation during rollout.

API
----
normalize_equity(equity_bars: Sequence[EquityBar], *, mode: Literal['compare','normalized']) -> Union[Tuple[List[EquityBar], List[EquityBar]], List[EquityBar]]

Design Notes
------------
- Legacy path historically scaled NAV and derived fields (peak_nav, drawdown) by an arbitrary factor (1_000_000). We eliminate this.
- During transition we produce both sequences (legacy_scaled, normalized) when mode='compare'.
- Normalization: divide all NAV-like monetary magnitude fields by SCALE_FACTOR (1_000_000) if legacy was scaled up. If code has already migrated and values are idempotent (no scaling present), heuristic early exit leaves them unchanged.
- Determinism: ordering preserved, inputs not mutated (return new list copies).
- Hashing: The *normalized* series is NOT automatically hashed yet. Call sites must decide which version participates in equity_signature to avoid hash drift until flag enable.

Future
------
Once normalization stable and tests (T031, T092) pass, we can switch default hashing to normalized and update documentation before removing compare mode.
"""

from __future__ import annotations

from copy import copy
from typing import List, Literal, Sequence, Tuple, Union

try:
    from models.equity_bar import EquityBar  # type: ignore
except ImportError:  # pragma: no cover - defensive for isolated module tests
    from alphaforge_brain.src.models.equity_bar import EquityBar

SCALE_FACTOR = 1_000_000.0
_HEURISTIC_MIN_MEAN_NAV = (
    10_000  # if mean(nav) is extremely large relative to 1.0 assume scaled
)

Mode = Literal["compare", "normalized"]


def _is_scaled(bars: Sequence[EquityBar]) -> bool:
    if not bars:
        return False
    # Simple heuristic: If median nav >> 1_000 assume scaling factor present.
    # Using median for robustness.
    values = sorted(b.nav for b in bars)
    mid = len(values) // 2
    median = (
        values[mid] if len(values) % 2 == 1 else (values[mid - 1] + values[mid]) / 2
    )
    return median > _HEURISTIC_MIN_MEAN_NAV


def _normalize_bar(bar: EquityBar) -> EquityBar:
    # Create shallow copy dict then instantiate new EquityBar to preserve immutability semantics
    d = bar.model_dump()
    # Fields treated as monetary magnitude: nav, peak_nav
    d["nav"] = d["nav"] / SCALE_FACTOR
    d["peak_nav"] = d["peak_nav"] / SCALE_FACTOR
    # drawdown represented as (nav - peak_nav)/peak_nav or similar already; preserve original ratio
    # If drawdown was computed on scaled values it is already scale-invariant, so leave as-is.
    return EquityBar(**d)


def _denormalize_bar(bar: EquityBar) -> EquityBar:
    d = bar.model_dump()
    d["nav"] = d["nav"] * SCALE_FACTOR
    d["peak_nav"] = d["peak_nav"] * SCALE_FACTOR
    return EquityBar(**d)


def normalize_equity(
    equity_bars: Sequence[EquityBar], *, mode: Mode = "compare"
) -> Union[Tuple[List[EquityBar], List[EquityBar]], List[EquityBar]]:
    """Normalize equity series.

    Parameters
    ----------
    equity_bars : Sequence[EquityBar]
        Original (possibly scaled) equity bars.
    mode : 'compare' | 'normalized'
        'compare' returns (legacy_scaled_sequence, normalized_sequence)
        'normalized' returns only the normalized sequence.

    Returns
    -------
    Either a pair (legacy, normalized) or a single normalized list depending on mode.
    """
    legacy_list = list(equity_bars)  # do not mutate caller list
    if not legacy_list:
        return (legacy_list, legacy_list) if mode == "compare" else legacy_list

    if _is_scaled(legacy_list):
        normalized = [_normalize_bar(b) for b in legacy_list]
    else:
        # Already normalized (or extremely small test values) => treat copy as normalized
        normalized = [copy(b) for b in legacy_list]

    if mode == "compare":
        return legacy_list, normalized
    return normalized


__all__ = ["normalize_equity", "SCALE_FACTOR"]

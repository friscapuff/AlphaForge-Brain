"""Feature flag helpers.

T016 - Feature Flags Scaffolding

Environment Variables:
  AF_UNIFIED_TRADES=1             Enable canonical Fill/CompletedTrade emission & adapters
  AF_EQUITY_NORMALIZER_V2=1       Enable unscaled equity normalization path (compare mode)
  AF_EQUITY_HASH_V2=1             Transitional: hash normalized equity series instead of legacy scaled input (NOT ACTIVE YET)

The new ``AF_EQUITY_HASH_V2`` toggle is a placeholder for the upcoming
transition where the equity hash (and eventually run hash) will switch to
use the normalized equity sequence. Until tasks T036-T038 are implemented
this flag is unused; keeping it here early allows downstream documentation
and tooling to reference a stable name.

Functions kept tiny & pure for easy monkeypatching in tests.
"""

from __future__ import annotations

import os
from functools import lru_cache

_DEF_TRUE = {"1", "true", "yes", "on", "enabled"}


@lru_cache(maxsize=1)
def is_unified_trades_enabled() -> bool:
    return os.getenv("AF_UNIFIED_TRADES", "0").lower() in _DEF_TRUE


@lru_cache(maxsize=1)
def is_equity_normalizer_v2_enabled() -> bool:
    return os.getenv("AF_EQUITY_NORMALIZER_V2", "0").lower() in _DEF_TRUE


@lru_cache(maxsize=1)
def is_equity_hash_v2_enabled() -> bool:
    """Return True if transitional normalized-equity hashing should be used.

    NOTE: Placeholder - no callers yet (T036). Adding early ensures tests &
    docs can refer to a concrete symbol without churn.
    """
    return os.getenv("AF_EQUITY_HASH_V2", "0").lower() in _DEF_TRUE


__all__ = [
    "is_unified_trades_enabled",
    "is_equity_normalizer_v2_enabled",
    "is_equity_hash_v2_enabled",
]

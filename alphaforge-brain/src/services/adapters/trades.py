"""Adapters module removed (T070).

This module was deprecated and is now removed as part of Phase 7 (T070 - Remove
Deprecated Shims). Any remaining imports should be migrated to canonical
models/flows directly.
"""

from __future__ import annotations

raise ImportError(
    "services.adapters.trades has been removed in Phase 7 (T070). "
    "Migrate callers to canonical CompletedTrade/Fill flows."
)

__all__: list[str] = []

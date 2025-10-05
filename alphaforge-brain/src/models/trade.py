"""Deprecated legacy trade model (T070).

This module has been removed in Phase 7. Do not import from here. Use
canonical Fill/CompletedTrade flows and duck-typed structures in services.
"""

from __future__ import annotations

raise ImportError(
    "models.trade has been removed in Phase 7 (T070). Use Fill/CompletedTrade and services APIs."
)

__all__: list[str] = []

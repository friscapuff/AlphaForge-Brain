"""Retention pruning service.

Current in-memory implementation prunes oldest completed runs beyond a limit.
Assumptions:
- InMemoryRunRegistry.store uses run_hash -> record mapping.
- Record has at least keys: 'hash', 'summary', 'validation_summary', 'p_values', 'progress_events'.
- We add 'created_at' timestamp when first seen here if absent (monotonic counter fallback).

Future (SQLite) version will translate this logic to DELETE ... WHERE id IN (...)
with ordering by created_at.
"""
from __future__ import annotations

import time
from typing import Any

from .create import InMemoryRunRegistry


def _ensure_created_ts(registry: InMemoryRunRegistry) -> None:
    for rec in registry.store.values():  # pragma: no cover (simple metadata normalization)
        if "created_at" not in rec:
            rec["created_at"] = time.time()


def prune(registry: InMemoryRunRegistry, limit: int = 100) -> dict[str, Any]:
    """Prune oldest runs past limit.

    Returns summary dict: { 'removed': [hashes], 'remaining': int, 'limit': int }
    Safety: does not remove if current size <= limit.
    """
    size = len(registry.store)
    if size <= limit:
        return {"removed": [], "remaining": size, "limit": limit}

    _ensure_created_ts(registry)
    # Sort by created_at ascending -> oldest first
    ordered: list[tuple[str, dict[str, Any]]] = sorted(
        registry.store.items(), key=lambda kv: kv[1].get("created_at", 0.0)
    )

    to_remove_count = size - limit
    removed: list[str] = []
    for i in range(to_remove_count):
        run_hash, _ = ordered[i]
        removed.append(run_hash)
        del registry.store[run_hash]

    return {"removed": removed, "remaining": len(registry.store), "limit": limit}


__all__ = ["prune"]

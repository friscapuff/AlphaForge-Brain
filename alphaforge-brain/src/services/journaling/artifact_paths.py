"""Filesystem helpers for enriched journaling artifacts.

Decision 3 budgets for bursts of eight trust-gate evaluations per minute, so
artifact writers should use the shared root defined here to avoid path drift
and to facilitate retention sweeps.
"""

from __future__ import annotations

from pathlib import Path

JOURNALING_ROOT = Path("zz_artifacts/journaling")


def resolve_journaling_root(base_dir: Path | None = None) -> Path:
    """Return the journaling artifact directory, ensuring it exists."""

    root = (base_dir or JOURNALING_ROOT).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


__all__ = ["JOURNALING_ROOT", "resolve_journaling_root"]

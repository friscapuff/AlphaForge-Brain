"""Permutation backend interface stub (Task T077, FR-044 placeholder).

Provides a future pluggable abstraction for distributed / parallel permutation execution.
Currently non-executable and unused to avoid premature complexity.
"""
from __future__ import annotations

from typing import Protocol, Iterable, Sequence

class PermutationBackend(Protocol):  # pragma: no cover - placeholder
    def run_trials(self, base_seed: int, trial_count: int, payload: dict) -> Sequence[float]:
        """Execute permutation trials and return ordered distribution of statistics.

        Determinism Requirement (future enforcement):
        - Returned sequence must be ordered by trial index (0..trial_count-1).
        - Any parallelization must not change statistical values relative to serial baseline.
        - Payload is an opaque mapping (strategy & data context) defined later.
        """
        ...

# Placeholder local backend reference (not implemented)
DEFAULT_BACKEND: PermutationBackend | None = None

__all__ = ["PermutationBackend", "DEFAULT_BACKEND"]

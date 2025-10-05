from __future__ import annotations

"""Pinned runtime dependency versions for determinism guard tests.

This captures the versions of critical numerical libraries whose changes can
impact floating point behavior or algorithmic outputs affecting reproducibility.

If these versions intentionally change, update this file and corresponding tests.
"""

PINNED = {
    "numpy": "2.0.2",  # CI-aligned (Poetry lock). numba 0.60 requires numpy <2.1; update with rationale if changed.
}

__all__ = ["PINNED"]

from __future__ import annotations

"""Pinned runtime dependency versions for determinism guard tests.

This captures the versions of critical numerical libraries whose changes can
impact floating point behavior or algorithmic outputs affecting reproducibility.

If these versions intentionally change, update this file and corresponding tests.
"""

PINNED = {
    "numpy": "2.0.2",  # synced to env (test guard). If upgrading, cite rationale (perf/security) in tasks.md.
}

__all__ = ["PINNED"]

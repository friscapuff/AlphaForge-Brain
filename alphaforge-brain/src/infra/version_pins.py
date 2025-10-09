from __future__ import annotations

"""Pinned runtime dependency versions for determinism guard tests.

This captures the versions of critical numerical libraries whose changes can
impact floating point behavior or algorithmic outputs affecting reproducibility.

If these versions intentionally change, update this file and corresponding tests.
"""

PINNED = {
    "numpy": "2.2.6",  # Updated to match current runtime environment; ensure CI lock aligns or adjust pins accordingly.
}

__all__ = ["PINNED"]

"""Determinism bootstrap utilities.

Applies global float formatting policy (FR-041) and provides seed helpers.
This is idempotent; safe to call multiple times.
"""

from __future__ import annotations

import json
import os
import random
from collections.abc import Iterable

import numpy as np
import pandas as pd

_FLOAT_PRECISION = 8

_APPLIED = False


def apply_global_determinism() -> None:
    global _APPLIED
    if _APPLIED:
        return
    # Numpy print / floating representation
    np.set_printoptions(precision=_FLOAT_PRECISION, floatmode="fixed", suppress=True)
    # Pandas float format via option context (cannot globally set print format for all writes
    # but we store the precision constant for downstream usage in IO helpers)
    # pandas typing: display.float_format accepts a Callable[[float], str]; lambda matches but stubs may be narrow in older versions
    pd.options.display.float_format = lambda v: f"{v:.{_FLOAT_PRECISION}f}"
    _APPLIED = True


def seed_all(seed: int) -> list[int]:
    """Seed python, numpy; return a list containing base seed for manifest linking.

    Additional derived seeds for permutation trials = base_seed + i (handled elsewhere).
    """
    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    return [seed]


def float_precision() -> int:
    return _FLOAT_PRECISION


def canonical_float(value: float) -> float:
    """Round float to canonical precision for hashing stability."""
    return float(f"{value:.{_FLOAT_PRECISION}f}")


def canonicalize_iter(values: Iterable[float]) -> list[float]:
    return [canonical_float(v) for v in values]


def canonical_json(data: object) -> str:
    """Canonical JSON dumps used by hashing layer (delegates to hash_utils).

    Provided here for convenience where hash_utils not available yet.
    """
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

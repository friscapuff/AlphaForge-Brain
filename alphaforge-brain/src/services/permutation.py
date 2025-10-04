"""Permutation / bootstrap engine (T040).

Generates deterministic shuffled indices for permutation tests and simple
bootstrap resamples using a provided seed.
"""

from __future__ import annotations

import random


def permutation_indices(n: int, trials: int, seed: int) -> list[list[int]]:
    rng = random.Random(seed)
    base = list(range(n))
    out: list[list[int]] = []
    for _ in range(trials):
        perm = base[:]
        rng.shuffle(perm)
        out.append(perm)
    return out


def bootstrap_indices(n: int, trials: int, seed: int) -> list[list[int]]:
    rng = random.Random(seed ^ 0xABCDEF)
    out: list[list[int]] = []
    for _ in range(trials):
        out.append([rng.randrange(0, n) for _ in range(n)])
    return out


__all__ = ["bootstrap_indices", "permutation_indices"]

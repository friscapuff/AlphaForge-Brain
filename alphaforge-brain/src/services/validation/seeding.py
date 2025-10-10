from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np


@dataclass(frozen=True)
class ValidationSeedBundle:
    """Deterministic seed container for Masters validation modules."""

    seed_root: int
    permutation: tuple[int, ...]
    optimizer: int
    cross_validation: int
    realism: int

    def as_mapping(self) -> dict[str, int | Sequence[int]]:
        return {
            "seed_root": self.seed_root,
            "permutation": self.permutation,
            "optimizer": self.optimizer,
            "cross_validation": self.cross_validation,
            "realism": self.realism,
        }


def derive_seed_bundle(
    *, seed_root: int, permutation_trials: int
) -> ValidationSeedBundle:
    """Generate deterministic seeds for validation components.

    Parameters
    ----------
    seed_root:
        Base seed configured for the run. When zero a default constant is used so
        callers receive a stable bundle instead of an empty seed set.
    permutation_trials:
        Number of permutation universes requested. The bundle always contains at
        least ``permutation_trials`` seeds so downstream engines can execute the
        desired number of shuffles without falling back to random derivations.
    """

    root = int(seed_root or 0x010AF043)
    trials = max(int(permutation_trials), 1)

    rng = np.random.default_rng(root)
    permutation = tuple(int(v) for v in rng.integers(0, 2**31 - 1, size=trials))
    optimizer = int(rng.integers(0, 2**31 - 1))
    cross_validation = int(rng.integers(0, 2**31 - 1))
    realism = int(rng.integers(0, 2**31 - 1))
    return ValidationSeedBundle(
        seed_root=root,
        permutation=permutation,
        optimizer=optimizer,
        cross_validation=cross_validation,
        realism=realism,
    )


__all__ = ["ValidationSeedBundle", "derive_seed_bundle"]

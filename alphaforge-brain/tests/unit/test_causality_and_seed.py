from __future__ import annotations

import pytest
from src.infra.utils.seed import derive_seed
from src.services.causality_guard import (
    CausalityGuard,
    CausalityMode,
    causality_context,
)


def test_causality_guard_permissive_records() -> None:
    g = CausalityGuard(CausalityMode.PERMISSIVE)
    g.record("feature_x", 2, detail=None)
    assert len(g.violations) == 1
    assert g.violations[0].offset == 2


def test_causality_guard_strict_raises() -> None:
    g = CausalityGuard(CausalityMode.STRICT)
    with pytest.raises(RuntimeError):
        g.record("f", 1)


def test_causality_context_manager() -> None:
    with causality_context(CausalityMode.PERMISSIVE) as cg:
        cg.record("f", 3)
        assert len(cg.violations) == 1


def test_derive_seed_deterministic_and_distinct() -> None:
    a = derive_seed(123, namespace="bootstrap", index=0)
    b = derive_seed(123, namespace="bootstrap", index=0)
    c = derive_seed(123, namespace="bootstrap", index=1)
    d = derive_seed(124, namespace="bootstrap", index=0)
    assert a == b
    assert a != c
    assert a != d
    assert 0 <= a < 2**32

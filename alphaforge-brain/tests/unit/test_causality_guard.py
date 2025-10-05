import pytest
from src.services.causality_guard import (
    CausalityGuard,
    CausalityMode,
    causality_context,
)


def test_permissive_collects_violations():
    guard = CausalityGuard(CausalityMode.PERMISSIVE)
    guard.record("feature_x", 1)
    guard.record("feature_x", 2)
    assert len(guard.violations) == 2
    # Non-positive offset ignored
    guard.record("feature_x", 0)
    assert len(guard.violations) == 2


def test_strict_raises_on_violation():
    guard = CausalityGuard(CausalityMode.STRICT)
    with pytest.raises(RuntimeError):
        guard.record("feat", 1)


def test_context_manager_usage():
    with causality_context(CausalityMode.PERMISSIVE) as g:
        g.record("f", 1)
    assert len(g.violations) == 1

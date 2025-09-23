from __future__ import annotations

import pytest

from services.causality_guard import CausalityGuard, CausalityMode


def test_causality_guard_modes() -> None:  # T012
    # Strict mode should raise on violation
    strict = CausalityGuard(CausalityMode.STRICT)
    with pytest.raises(RuntimeError):
        strict.record_violation("feature_x", 1, "peeking ahead")

    # Permissive mode should collect violation instead of raising
    perm = CausalityGuard(CausalityMode.PERMISSIVE)
    perm.record_violation("feature_x", 2, "lookahead allowed")
    v = perm.violations
    assert len(v) == 1
    assert v[0].feature == "feature_x"
    assert v[0].offset == 2

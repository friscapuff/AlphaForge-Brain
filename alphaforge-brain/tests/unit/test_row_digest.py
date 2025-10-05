from __future__ import annotations

import pytest
from src.infra.utils.hash import row_digest


@pytest.mark.unit
@pytest.mark.determinism
def test_row_digest_stable_key_order():
    a = {"ts": 1, "pnl": 2.5, "side": "buy"}
    b = {"side": "buy", "pnl": 2.5, "ts": 1}
    assert row_digest(a) == row_digest(b)

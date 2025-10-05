"""Strategy Registry Metadata Integration (T017)

Ensures optional metadata registration for strategies is deterministic and
retrievable; verifies that re-registering overwrites with canonical key order.
"""

from __future__ import annotations

from services.strategy_registry import StrategyRegistry


def test_strategy_registry_metadata() -> None:  # T017
    reg = StrategyRegistry()
    reg.register(
        "dual_sma", {"description": "Dual moving average crossover", "version": "1.0"}
    )
    meta = reg.get("dual_sma")
    assert meta is not None
    assert meta["version"] == "1.0"
    assert set(meta.keys()) == {"description", "version"}

    # Overwrite with additional field (should replace)
    reg.register(
        "dual_sma",
        {
            "version": "1.1",
            "description": "Dual moving average crossover",
            "category": "momentum",
        },
    )
    meta2 = reg.get("dual_sma")
    assert meta2 is not None
    assert meta2["version"] == "1.1"
    assert "category" in meta2
    # Deterministic ordering via sorted insertion
    assert list(meta2.keys()) == sorted(meta2.keys())

    # all() returns deep copies
    all_copy = reg.all()
    assert "dual_sma" in all_copy
    all_copy["dual_sma"]["version"] = "MUTATE"
    assert reg.get("dual_sma")["version"] == "1.1"


__all__ = ["test_strategy_registry_metadata"]

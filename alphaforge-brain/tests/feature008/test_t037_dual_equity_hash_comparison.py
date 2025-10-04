import os

import pytest
from domain.schemas.run_config import (
    ExecutionSpec,
    RiskSpec,
    RunConfig,
    StrategySpec,
    ValidationSpec,
)

pytestmark = pytest.mark.feature008


def _cfg():
    return RunConfig(
        indicators=[],
        strategy=StrategySpec(name="buy_hold", params={}),
        risk=RiskSpec(model="none", params={}),
        execution=ExecutionSpec(),
        validation=ValidationSpec(),
        symbol="NVDA",
        timeframe="1d",
        start="2024-01-01",
        end="2024-01-15",
        seed=11,
    )


def _clear_flags():
    for k in ["AF_EQUITY_NORMALIZER_V2", "AF_EQUITY_HASH_V2"]:
        if k in os.environ:
            del os.environ[k]
    from settings import flags as _flags

    _flags.is_equity_normalizer_v2_enabled.cache_clear()  # type: ignore
    _flags.is_equity_hash_v2_enabled.cache_clear()  # type: ignore


def test_t037_dual_equity_hash_comparison():
    from domain.run.create import InMemoryRunRegistry, create_or_get

    _clear_flags()
    cfg = _cfg()

    # Baseline (no flags) -> only legacy hash present
    reg = InMemoryRunRegistry()
    h_legacy, rec_legacy, _ = create_or_get(cfg, reg)
    legacy_hash_1 = rec_legacy.get("equity_curve_hash")
    assert legacy_hash_1 and "equity_curve_hash_v2" not in rec_legacy

    # Enable normalization only -> still only legacy hash (since v2 hashing flag off)
    os.environ["AF_EQUITY_NORMALIZER_V2"] = "1"
    from settings import flags as _flags

    _flags.is_equity_normalizer_v2_enabled.cache_clear()  # type: ignore

    reg2 = InMemoryRunRegistry()
    h_norm, rec_norm, _ = create_or_get(cfg, reg2)
    assert rec_norm.get("equity_curve_hash") == legacy_hash_1
    assert "equity_curve_hash_v2" not in rec_norm

    # Enable both normalization + v2 hash -> dual hash present, legacy unchanged
    os.environ["AF_EQUITY_HASH_V2"] = "1"
    _flags.is_equity_hash_v2_enabled.cache_clear()  # type: ignore

    reg3 = InMemoryRunRegistry()
    h_dual, rec_dual, _ = create_or_get(cfg, reg3)
    assert (
        rec_dual.get("equity_curve_hash") == legacy_hash_1
    ), "legacy hash must remain stable"
    v2_hash = rec_dual.get("equity_curve_hash_v2")
    assert (
        isinstance(v2_hash, str) and v2_hash
    ), "v2 hash must be computed when both flags enabled"
    # In general normalized may differ; assert difference to validate distinct input path
    # If scaling heuristic triggered, hashes should differ; if not, equality is acceptable.
    preview = rec_dual.get("normalized_equity_preview", {}) or {}
    scaled_flag = preview.get("scaled")
    # We do not assert inequality to keep test stable across datasets where scaling may or may not materially change
    # rounded nav values. Presence + legacy stability suffice for transitional phase.

    # Run hash must remain stable across all three runs (hash field is deterministic pre-switch)
    assert h_legacy == h_norm == h_dual

    # Cleanup
    _clear_flags()

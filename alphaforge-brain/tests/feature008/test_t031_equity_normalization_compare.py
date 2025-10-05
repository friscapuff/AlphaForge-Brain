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


def _enable_flag():
    os.environ["AF_EQUITY_NORMALIZER_V2"] = "1"
    from settings import flags as _flags

    _flags.is_equity_normalizer_v2_enabled.cache_clear()  # type: ignore


def _disable_flag():
    # Phase 7 semantics: default is ON; explicitly set to a falsey value to disable
    os.environ["AF_EQUITY_NORMALIZER_V2"] = "0"
    from settings import flags as _flags

    _flags.is_equity_normalizer_v2_enabled.cache_clear()  # type: ignore


def _make_cfg():
    return RunConfig(
        indicators=[],
        strategy=StrategySpec(name="buy_hold", params={}),
        risk=RiskSpec(model="none", params={}),
        execution=ExecutionSpec(),
        validation=ValidationSpec(),
        symbol="NVDA",
        timeframe="1d",
        start="2024-01-01",
        end="2024-02-01",
        seed=1,
    )


@pytest.fixture(autouse=True)
def _cleanup_flag():
    if "AF_EQUITY_NORMALIZER_V2" in os.environ:
        del os.environ["AF_EQUITY_NORMALIZER_V2"]
    from settings import flags as _flags

    _flags.is_equity_normalizer_v2_enabled.cache_clear()  # type: ignore
    yield
    if "AF_EQUITY_NORMALIZER_V2" in os.environ:
        del os.environ["AF_EQUITY_NORMALIZER_V2"]
    _flags.is_equity_normalizer_v2_enabled.cache_clear()  # type: ignore


def test_t031_equity_normalization_compare_smoke():
    from domain.run.create import InMemoryRunRegistry, create_or_get

    cfg = _make_cfg()
    reg = InMemoryRunRegistry()

    # Baseline (Phase 7 default: flag ON)
    h1, rec1, _ = create_or_get(cfg, reg)
    assert "normalized_equity_preview" in rec1

    # Disable flag (new registry to avoid cached reuse)
    _disable_flag()
    reg2 = InMemoryRunRegistry()
    h2, rec2, _ = create_or_get(cfg, reg2)
    assert h1 == h2
    assert "normalized_equity_preview" not in rec2


def test_t031_idempotent_disable_enable_cycle():
    from domain.run.create import InMemoryRunRegistry, create_or_get

    cfg = _make_cfg()
    # Start with default ON
    reg_on1 = InMemoryRunRegistry()
    h_on1, rec_on1, _ = create_or_get(cfg, reg_on1)
    assert "normalized_equity_preview" in rec_on1
    # Disable
    _disable_flag()
    reg_off = InMemoryRunRegistry()
    h_off, rec_off, _ = create_or_get(cfg, reg_off)
    assert "normalized_equity_preview" not in rec_off
    # Re-enable
    _enable_flag()
    reg_on2 = InMemoryRunRegistry()
    h_on2, rec_on2, _ = create_or_get(cfg, reg_on2)
    assert "normalized_equity_preview" in rec_on2
    # Hash stability across toggles
    assert h_on1 == h_off == h_on2

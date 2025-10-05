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


def _set_flag(val: bool):
    from settings import flags as _flags

    if val:
        os.environ["AF_EQUITY_NORMALIZER_V2"] = "1"
    else:
        if "AF_EQUITY_NORMALIZER_V2" in os.environ:
            del os.environ["AF_EQUITY_NORMALIZER_V2"]
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
        seed=2,
    )


@pytest.fixture(autouse=True)
def _clean():
    if "AF_EQUITY_NORMALIZER_V2" in os.environ:
        del os.environ["AF_EQUITY_NORMALIZER_V2"]
    from settings import flags as _flags

    _flags.is_equity_normalizer_v2_enabled.cache_clear()  # type: ignore
    yield
    if "AF_EQUITY_NORMALIZER_V2" in os.environ:
        del os.environ["AF_EQUITY_NORMALIZER_V2"]
    _flags.is_equity_normalizer_v2_enabled.cache_clear()  # type: ignore


def test_t092_metrics_hash_stability():
    from domain.run.create import InMemoryRunRegistry, create_or_get

    cfg = _make_cfg()

    reg1 = InMemoryRunRegistry()
    _set_flag(False)
    h_off, rec_off, _ = create_or_get(cfg, reg1)
    metrics_hash_off = rec_off.get("metrics_hash")
    equity_hash_off = rec_off.get("equity_curve_hash")

    reg2 = InMemoryRunRegistry()
    _set_flag(True)
    h_on, rec_on, _ = create_or_get(cfg, reg2)
    metrics_hash_on = rec_on.get("metrics_hash")
    equity_hash_on = rec_on.get("equity_curve_hash")

    # Phase 3 intent: metrics hash must remain identical, equity hash unchanged (still using legacy input) & run hash stable
    assert h_off == h_on, "run hash must stay stable before switching hashing input"
    assert (
        metrics_hash_off == metrics_hash_on
    ), "metrics hash must not drift due to normalization preview"
    assert (
        equity_hash_off == equity_hash_on
    ), "equity hash must not change until we opt-in hashing normalized series"

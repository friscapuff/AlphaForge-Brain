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


def _cfg(seed=123):
    return RunConfig(
        indicators=[],
        strategy=StrategySpec(
            name="buy_hold", params={}
        ),  # buy/hold should produce no round-trip exits inside short window
        risk=RiskSpec(model="none", params={}),
        execution=ExecutionSpec(),
        validation=ValidationSpec(),
        symbol="NVDA",
        timeframe="1d",
        start="2024-01-01",
        end="2024-01-03",  # very small range to avoid trades
        seed=seed,
    )


@pytest.fixture(autouse=True)
def _clean_flags():
    # Ensure unified trades flag off so we rely on adapter (or absence) consistently
    if "AF_UNIFIED_TRADES" in os.environ:
        del os.environ["AF_UNIFIED_TRADES"]
    yield
    if "AF_UNIFIED_TRADES" in os.environ:
        del os.environ["AF_UNIFIED_TRADES"]


def test_t085_empty_completed_trade_set_stability():
    from domain.run.create import InMemoryRunRegistry, create_or_get

    cfg = _cfg()
    reg = InMemoryRunRegistry()
    h, rec, _ = create_or_get(cfg, reg)

    # Completed trades may surface in summary or validation in future; for now assert absence OR empty semantics
    summary = rec.get("summary", {}) or {}
    completed = summary.get("completed_trades") or []
    assert isinstance(completed, (list, tuple))
    assert (
        len(completed) == 0
    ), "Expected no completed trades for trivial buy_hold window"

    # Metrics hash should exist and be stable on re-run
    metrics_hash_1 = rec.get("metrics_hash")
    assert metrics_hash_1 is not None

    # Re-run identical config (cache hit) -> same hash and metrics hash
    h2, rec2, created2 = create_or_get(cfg, reg)
    assert created2 is False
    assert h2 == h
    assert rec2.get("metrics_hash") == metrics_hash_1

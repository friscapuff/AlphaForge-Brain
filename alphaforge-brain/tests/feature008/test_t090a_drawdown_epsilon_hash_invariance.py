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

# This granular test crafts borderline EquityBar scenarios indirectly by running a short config twice
# under two epsilon settings and asserting the metrics hash remains stable (normalization preview only).
# It complements T090 which focuses on override mechanics & absence of validation failure.


def _cfg(seed=777):
    return RunConfig(
        indicators=[],
        strategy=StrategySpec(name="buy_hold", params={}),
        risk=RiskSpec(model="none", params={}),
        execution=ExecutionSpec(),
        validation=ValidationSpec(),
        symbol="NVDA",
        timeframe="1d",
        start="2024-01-01",
        end="2024-01-10",
        seed=seed,
    )


def _run(cfg):
    from domain.run.create import InMemoryRunRegistry, create_or_get

    reg = InMemoryRunRegistry()
    h, rec, _ = create_or_get(cfg, reg)
    return h, rec


@pytest.mark.parametrize("eps_low,eps_high", [("1e-9", "1e-6")])
def test_t090a_drawdown_epsilon_hash_invariance(eps_low, eps_high):
    # First run with tight epsilon
    os.environ["AF_DRAWNDOWN_EPSILON"] = eps_low
    from settings import determinism as det

    det._load.cache_clear()  # type: ignore

    cfg = _cfg()
    h_low, rec_low = _run(cfg)
    metrics_hash_low = rec_low.get("metrics_hash")
    equity_hash_low = rec_low.get("equity_curve_hash")

    assert metrics_hash_low and equity_hash_low

    # Second run with wider epsilon
    os.environ["AF_DRAWNDOWN_EPSILON"] = eps_high
    det._load.cache_clear()  # type: ignore
    h_high, rec_high = _run(cfg)

    assert (
        rec_high.get("metrics_hash") == metrics_hash_low
    ), "metrics hash must be invariant to epsilon drift"
    assert (
        rec_high.get("equity_curve_hash") == equity_hash_low
    ), "equity hash must stay legacy until AF_EQUITY_HASH_V2 enabled"
    assert h_low == h_high, "run hash must remain stable pre-hash-transition"

    # Cleanup env
    del os.environ["AF_DRAWNDOWN_EPSILON"]
    det._load.cache_clear()  # type: ignore

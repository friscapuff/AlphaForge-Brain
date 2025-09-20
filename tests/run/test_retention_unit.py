from domain.run.create import InMemoryRunRegistry, create_or_get
from domain.schemas.run_config import (
    ExecutionSpec,
    IndicatorSpec,
    RiskSpec,
    RunConfig,
    StrategySpec,
    ValidationSpec,
)

# Minimal RunConfig constructor helper consistent with earlier tests

def make_config(seed: int):
    return RunConfig(
        symbol="TEST",
        timeframe="1m",
        start="2024-01-01",
        end="2024-01-02",
        initial_equity=10000.0,
        indicators=[IndicatorSpec(name="dual_sma", params={"fast": 5, "slow": 20})],
        strategy=StrategySpec(name="dual_sma", params={}),
        risk=RiskSpec(name="fixed_fraction", model="fixed_fraction", params={"fraction": 0.1}),
        execution=ExecutionSpec(slippage_bps=1, fee_perc=0.0005),
        validation=ValidationSpec(permutation=None, block_bootstrap=None, monte_carlo=None, walk_forward=None),
        seed=seed,
    )


def test_retention_prune_oldest_after_exceeding_limit():
    registry = InMemoryRunRegistry()

    # Insert 105 runs with monotonically increasing fake start_ts
    created_ids = []
    for i in range(105):
        cfg = make_config(seed=i)
        h, rec, created = create_or_get(cfg, registry, seed=i)
        assert created is True
        created_ids.append(h)

    # Because create_or_get integrates pruning, size should already be capped at 100
    assert len(registry.store) == 100

    from domain.run.retention import prune

    # Additional prune call should be a no-op now
    summary = prune(registry, limit=100)
    assert summary["removed"] == []
    assert summary["remaining"] == 100
    last_hash = created_ids[-1]
    assert last_hash in registry.store

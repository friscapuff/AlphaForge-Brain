from domain.schemas.run_config import (
    ExecutionSpec,
    IndicatorSpec,
    RiskSpec,
    RunConfig,
    StrategySpec,
)


def _config():
    return RunConfig(
        indicators=[IndicatorSpec(name="dual_sma", params={"fast": 5, "slow": 15})],
        strategy=StrategySpec(name="dual_sma", params={"short_window": 5, "long_window": 15}),
        risk=RiskSpec(model="fixed_fraction", params={"fraction": 0.1}),
        execution=ExecutionSpec(mode="sim", fee_bps=2.0, slippage_bps=2.0),
        symbol="CACHE",
        timeframe="1m",
        start="2024-01-01",
        end="2024-02-01",
    )


def test_create_or_get_idempotent():
    from domain.run.create import InMemoryRunRegistry, create_or_get
    cfg = _config()
    registry = InMemoryRunRegistry()
    h1, rec1, created1 = create_or_get(cfg, registry, seed=123)
    h2, rec2, created2 = create_or_get(cfg, registry, seed=999)  # different seed should not matter once cached
    assert h1 == h2
    assert created1 is True
    assert created2 is False
    # progress events count should be present and not increment on second call
    assert rec1["progress_events"] >= 2  # At least RUNNING + COMPLETE
    assert rec2["progress_events"] == rec1["progress_events"]
    # p-values may be absent if validation disabled; ensure key structure stable
    if "p_values" in rec1 and isinstance(rec1["p_values"], dict):
        assert "perm" in rec1["p_values"]
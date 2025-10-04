from __future__ import annotations

from domain.run.create import InMemoryRunRegistry, create_or_get
from domain.schemas.run_config import (
    ExecutionSpec,
    IndicatorSpec,
    RiskSpec,
    RunConfig,
    StrategySpec,
    ValidationSpec,
)


def _cfg(symbol: str = "NVDA") -> RunConfig:
    return RunConfig(
        symbol=symbol,
        timeframe="1d",
        start="2024-01-01",
        end="2024-01-03",
        indicators=[IndicatorSpec(name="sma", params={"window": 5})],
        strategy=StrategySpec(name="dual_sma", params={"fast": 5, "slow": 15}),
        risk=RiskSpec(model="fixed_fraction", params={"fraction": 0.1}),
        execution=ExecutionSpec(),
        validation=ValidationSpec(),
        seed=1,
    )


def test_retention_dataset_reuse_idempotent() -> None:
    reg = InMemoryRunRegistry()
    cfg = _cfg()
    h1, _, created1 = create_or_get(cfg, reg, seed=cfg.seed)
    assert created1
    h2, _, created2 = create_or_get(cfg, reg, seed=cfg.seed)
    assert not created2
    assert h1 == h2
    # Registry size should remain 1
    assert len(reg.store) == 1


def test_retention_prune_stability() -> None:
    reg = InMemoryRunRegistry()
    for i in range(105):  # exceed prune threshold (100)
        cfg = _cfg(symbol="NVDA")
        cfg.seed = i
        create_or_get(cfg, reg, seed=cfg.seed)
    # After creations, registry size should be at most 100
    assert len(reg.store) <= 100

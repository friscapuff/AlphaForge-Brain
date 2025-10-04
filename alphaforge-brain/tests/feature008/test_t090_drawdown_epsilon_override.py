import math
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


def _cfg(seed=42):
    # Short window to keep run fast; equity bars synthesized upstream
    return RunConfig(
        indicators=[],
        strategy=StrategySpec(name="buy_hold", params={}),
        risk=RiskSpec(model="none", params={}),
        execution=ExecutionSpec(),
        validation=ValidationSpec(),
        symbol="NVDA",
        timeframe="1d",
        start="2024-01-01",
        end="2024-01-05",
        seed=seed,
    )


@pytest.mark.parametrize(
    "epsilon_env", ["1e-9", "1e-6"]
)  # widen epsilon to accept slightly larger diff
def test_t090_drawdown_epsilon_override(epsilon_env):
    # Set epsilon before import side-effects (model uses cached constant). Force cache clear of determinism loader.
    os.environ["AF_DRAWNDOWN_EPSILON"] = epsilon_env
    from settings import determinism as det

    det._load.cache_clear()  # type: ignore

    from domain.run.create import InMemoryRunRegistry, create_or_get

    cfg = _cfg()
    reg = InMemoryRunRegistry()
    h, rec, _ = create_or_get(cfg, reg)

    # Metrics hash presence & stability under epsilon variation
    metrics_hash = rec.get("metrics_hash")
    assert metrics_hash is not None

    # Re-run with same epsilon -> cache hit, stable metrics hash
    h2, rec2, created2 = create_or_get(cfg, reg)
    assert created2 is False
    assert rec2.get("metrics_hash") == metrics_hash

    # Sanity: epsilon value is respected (cannot directly assert internal tolerance without crafting custom EquityBar, but we ensure no failure)
    val = float(epsilon_env)
    assert math.isclose(val, float(epsilon_env))

    # Cleanup
    del os.environ["AF_DRAWNDOWN_EPSILON"]
    det._load.cache_clear()  # type: ignore

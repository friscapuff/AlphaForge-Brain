from api.app import create_app
from domain.run.retention_policy import (
    RetentionConfig,
    apply_retention_plan,
    plan_retention,
)
from fastapi.testclient import TestClient

# NOTE: mean_rev strategy is a minimal test-only strategy declared in domain.strategy.mean_rev
# to exercise multi-strategy retention ranking logic.


def _seed_runs(
    client: TestClient,
    n: int,
    strategy: str,
    metric_base: float,
    pinned: set[int] | None = None,
):
    pinned = pinned or set()
    hashes = []
    for i in range(n):
        payload = {
            "indicators": [],
            "strategy": {"name": strategy, "params": {"fast": 5, "slow": 20}},
            "risk": {"model": "fixed_fraction", "params": {"fraction": 0.1}},
            "execution": {"mode": "sim"},
            "validation": {},
            "symbol": "NVDA",
            "timeframe": "1d",
            "start": "2024-01-01",
            "end": "2024-02-01",
            "seed": 1000 + i,
        }
        r = client.post("/runs", json=payload)
        h = r.json()["run_hash"]
        # Mutate registry directly to add ranking info
        reg = client.app.state.registry
        rec = reg.get(h)
        rec["strategy_name"] = strategy
        rec["primary_metric_value"] = metric_base + i
        if i in pinned:
            rec["pinned"] = True
        hashes.append(h)
    return hashes


def test_retention_plan_basic():
    app = create_app()
    client = TestClient(app)
    # Seed two strategies
    _seed_runs(client, 8, "dual_sma", 10.0, pinned={2})
    _seed_runs(client, 6, "mean_rev", 20.0)
    reg = client.app.state.registry
    cfg = RetentionConfig(keep_last=10, top_k_per_strategy=3)
    plan = plan_retention(reg, cfg)
    # Pinned must be kept
    assert any(
        rec.get("pinned") for h, rec in reg.store.items() if h in plan["keep_full"]
    )
    # Top-k per strategy limited
    # Ensure no strategy contributes more than 3 to top_k set
    strat_counts = {"dual_sma": 0, "mean_rev": 0}
    for h in plan["top_k"]:
        strat = reg.store[h].get("strategy_name")
        strat_counts[strat] += 1
    assert all(v <= 3 for v in strat_counts.values())


def test_retention_apply_marks_states():
    app = create_app()
    client = TestClient(app)
    _seed_runs(client, 5, "dual_sma", 10.0, pinned={1})
    reg = client.app.state.registry
    cfg = RetentionConfig(keep_last=2, top_k_per_strategy=1)
    plan = plan_retention(reg, cfg)
    apply_retention_plan(reg, plan)
    for _h, rec in reg.store.items():
        assert rec.get("retention_state") in {
            "pinned",
            "top_k",
            "full",
            "manifest-only",
        }
    # Demoted items should not be pinned
    for h in plan["demote"]:
        assert not reg.store[h].get("pinned")

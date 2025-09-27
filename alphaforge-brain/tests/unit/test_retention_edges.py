from domain.run.create import InMemoryRunRegistry
from domain.run.retention_policy import (
    RetentionConfig,
    apply_retention_plan,
    plan_retention,
)


def _mk_registry(entries):
    reg = InMemoryRunRegistry()
    for h, rec in entries:
        reg.store[h] = rec
    return reg


def test_retention_pin_overrides_demote_and_size_budget(tmp_path, monkeypatch):
    # Three runs; only size budget forces demotion of oldest non-pinned
    entries = [
        ("r1", {"created_at": 1, "primary_metric_value": 0.1, "pinned": True}),
        ("r2", {"created_at": 2, "primary_metric_value": 0.2}),
        ("r3", {"created_at": 3, "primary_metric_value": 0.3}),
    ]
    reg = _mk_registry(entries)
    # Keep last=3, top_k=1 per strategy, but apply tiny size budget forcing demotion except pinned
    cfg = RetentionConfig(keep_last=3, top_k_per_strategy=1, max_full_bytes=0)
    plan = plan_retention(reg, cfg)
    # r1 pinned always kept full; top_k likely r3 (highest metric)
    assert "r1" in plan["keep_full"]
    assert any(h in plan["keep_full"] for h in ("r2", "r3"))
    apply_retention_plan(reg, plan)
    assert reg.store["r1"]["retention_state"] == "pinned"


def test_retention_created_at_missing_defaults_zero():
    reg = _mk_registry(
        [
            ("a", {"primary_metric_value": 1.0}),
            ("b", {"primary_metric_value": 2.0}),
        ]
    )
    plan = plan_retention(reg, RetentionConfig(keep_last=1, top_k_per_strategy=0))
    # Only one keep_full due to keep_last=1
    assert len(plan["keep_full"]) == 1
    assert plan["demote"] | plan["keep_full"] == {"a", "b"}

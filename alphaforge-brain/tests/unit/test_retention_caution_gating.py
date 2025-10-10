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


def test_retention_excludes_caution_runs_from_promotion():
    # Three runs: r1 caution-flagged but newest and top metric; r2 normal; r3 pinned even if caution
    entries = [
        (
            "r1",
            {"created_at": 3, "primary_metric_value": 0.9, "validation_caution": True},
        ),
        (
            "r2",
            {"created_at": 2, "primary_metric_value": 0.8, "validation_caution": False},
        ),
        (
            "r3",
            {
                "created_at": 1,
                "primary_metric_value": 0.1,
                "validation_caution": True,
                "pinned": True,
            },
        ),
    ]
    reg = _mk_registry(entries)
    cfg = RetentionConfig(keep_last=2, top_k_per_strategy=1)
    plan = plan_retention(reg, cfg)
    # r1 is caution -> should not be in keep_full (excluded by gating), r3 pinned always kept
    assert "r3" in plan["keep_full"]
    assert "r1" not in plan["keep_full"], plan
    # r2 should be included to satisfy keep_last/top_k since r1 is excluded
    assert "r2" in plan["keep_full"], plan
    apply_retention_plan(reg, plan)
    assert reg.store["r3"]["retention_state"] == "pinned"
    assert reg.store["r1"]["retention_state"] == "manifest-only"
    assert reg.store["r2"]["retention_state"] in {"full", "top_k"}


def test_retention_excludes_significance_fail_from_promotion():
    entries = [
        (
            "r1",
            {
                "created_at": 3,
                "primary_metric_value": 0.95,
                "validation_significance": "fail",
            },
        ),
        (
            "r2",
            {"created_at": 2, "primary_metric_value": 0.9},
        ),
        (
            "r3",
            {"created_at": 1, "primary_metric_value": 0.4},
        ),
    ]
    reg = _mk_registry(entries)
    cfg = RetentionConfig(keep_last=2, top_k_per_strategy=1)
    plan = plan_retention(reg, cfg)
    assert "r1" not in plan["keep_full"], plan
    assert "r2" in plan["keep_full"], plan


def test_retention_allows_pinned_even_when_significance_fails():
    entries = [
        (
            "r1",
            {
                "created_at": 3,
                "primary_metric_value": 0.95,
                "validation_significance": "fail",
                "pinned": True,
            },
        ),
        (
            "r2",
            {"created_at": 2, "primary_metric_value": 0.9},
        ),
    ]
    reg = _mk_registry(entries)
    cfg = RetentionConfig(keep_last=2, top_k_per_strategy=1)
    plan = plan_retention(reg, cfg)
    assert "r1" in plan["keep_full"], plan


def test_retention_excludes_realism_fail_from_promotion():
    entries = [
        (
            "r1",
            {
                "created_at": 3,
                "primary_metric_value": 0.96,
                "validation_v2": {"execution_realism": {"status": "fail"}},
            },
        ),
        (
            "r2",
            {"created_at": 2, "primary_metric_value": 0.9},
        ),
        (
            "r3",
            {"created_at": 1, "primary_metric_value": 0.5},
        ),
    ]
    reg = _mk_registry(entries)
    cfg = RetentionConfig(keep_last=2, top_k_per_strategy=1)
    plan = plan_retention(reg, cfg)
    assert "r1" not in plan["keep_full"], plan
    assert "r2" in plan["keep_full"], plan


def test_retention_excludes_failed_checks_without_status_fields():
    entries = [
        (
            "r1",
            {
                "created_at": 3,
                "primary_metric_value": 0.9,
                "validation_failed_checks": ("execution_realism",),
            },
        ),
        (
            "r2",
            {"created_at": 2, "primary_metric_value": 0.85},
        ),
    ]
    reg = _mk_registry(entries)
    cfg = RetentionConfig(keep_last=2, top_k_per_strategy=1)
    plan = plan_retention(reg, cfg)
    assert "r1" not in plan["keep_full"], plan


def test_retention_uses_manifest_significance_metadata():
    entries = [
        (
            "r1",
            {
                "created_at": 3,
                "primary_metric_value": 0.96,
                "validation_v2": {
                    "manifest": {"validation_significance": "fail"},
                    "metadata": {"significance_status": "fail"},
                },
            },
        ),
        (
            "r2",
            {"created_at": 2, "primary_metric_value": 0.9},
        ),
    ]
    reg = _mk_registry(entries)
    cfg = RetentionConfig(keep_last=2, top_k_per_strategy=1)
    plan = plan_retention(reg, cfg)
    assert "r1" not in plan["keep_full"], plan
    assert "r2" in plan["keep_full"], plan

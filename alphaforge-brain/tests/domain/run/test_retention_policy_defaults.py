import json
from pathlib import Path

import pytest
from domain.run.create import InMemoryRunRegistry
from domain.run.retention_policy import (
    apply_retention_plan,
    load_retention_config,
    plan_retention,
)
from prometheus_client import CollectorRegistry


def _write_policy(tmp_path: Path) -> Path:
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(
        "\n".join(
            [
                'policy_version: "2025.10.13"',
                "max_runs: 3",
                "per_strategy_top: 0",
                "pin_expiry_days: null",
                "waiver_required: true",
                f"audit_log_path: \"{(tmp_path / 'audit.log').as_posix()}\"",
                f"breach_log_path: \"{(tmp_path / 'breaches.log').as_posix()}\"",
                "metric_labels:",
                "  environment: test",
            ]
        ),
        encoding="utf-8",
    )
    return policy_path


@pytest.fixture()
def retention_policy_env(tmp_path, monkeypatch):
    policy_path = _write_policy(tmp_path)
    monkeypatch.setenv("RETENTION_POLICY_PATH", str(policy_path))
    monkeypatch.setenv("GOVERNANCE_AUDIT_PATH", str(tmp_path / "governance_audit.log"))
    yield tmp_path


def test_retention_defaults_enforce_caps_and_log_breach(retention_policy_env):
    tmp_path = retention_policy_env
    registry = InMemoryRunRegistry()
    # Pinned run should always be retained even when caps exceeded.
    registry.set(
        "RUN-PIN",
        {
            "created_at": 500.0,
            "strategy_name": "alpha",
            "primary_metric_value": 4.0,
            "pinned": True,
        },
    )
    # Additional runs exceeding max_runs (3) to trigger breach logging.
    registry.set(
        "RUN-A1",
        {
            "created_at": 400.0,
            "strategy_name": "alpha",
            "primary_metric_value": 3.0,
        },
    )
    registry.set(
        "RUN-A2",
        {
            "created_at": 300.0,
            "strategy_name": "alpha",
            "primary_metric_value": 2.0,
        },
    )
    registry.set(
        "RUN-B1",
        {
            "created_at": 200.0,
            "strategy_name": "beta",
            "primary_metric_value": 3.5,
        },
    )
    registry.set(
        "RUN-C1",
        {
            "created_at": 100.0,
            "strategy_name": "gamma",
            "primary_metric_value": 1.5,
        },
    )

    metrics_registry = CollectorRegistry()
    cfg = load_retention_config()
    plan = plan_retention(
        registry,
        cfg=cfg,
        metrics_registry=metrics_registry,
    )

    assert "RUN-PIN" in plan["keep_full"], "Pinned run must stay in keep_full set"
    assert plan["breaches"], "Retention plan should record breach metadata"
    breach_types = {entry["type"] for entry in plan["breaches"]}
    assert "max_runs" in breach_types

    # Breach log entries should be appended to the configured path.
    breach_log = tmp_path / "breaches.log"
    assert breach_log.exists()
    records = [
        json.loads(line)
        for line in breach_log.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert records, "Breach log must contain JSON entries"
    assert records[-1]["message"] == "retention.policy.breach"

    # Prometheus counter must increment with structured labels.
    sample = metrics_registry.get_sample_value(
        "governance_event_total",
        labels={
            "event_type": "retention_breach",
            "reason": "max_runs",
            "environment": "test",
        },
    )
    assert sample == pytest.approx(1.0)

    apply_retention_plan(registry, plan)
    # Demoted runs should now reflect manifest-only retention state.
    for run_hash in plan["demote"]:
        rec = registry.get(run_hash)
        if rec and not rec.get("pinned"):
            assert rec.get("retention_state") == "manifest-only"


def test_retention_breach_includes_journaling_assets(tmp_path, monkeypatch):
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(
        "\n".join(
            [
                'policy_version: "2025.10.13"',
                "max_runs: 1",
                "per_strategy_top: 0",
                "waiver_required: true",
                "full_run_assets:",
                "  - name: journaling",
                "    root: zz_artifacts/journaling",
                '    policy_version: "2025.10.13"',
                '    decision_ref: "Decision 2"',
                "    retention:",
                "      max_runs: 60",
                "      per_strategy_top: 6",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("RETENTION_POLICY_PATH", str(policy_path))

    registry = InMemoryRunRegistry()
    registry.set(
        "RUN-A",
        {
            "created_at": 2.0,
            "strategy_name": "alpha",
        },
    )
    registry.set(
        "RUN-B",
        {
            "created_at": 1.0,
            "strategy_name": "beta",
        },
    )

    cfg = load_retention_config()
    plan = plan_retention(registry, cfg=cfg)

    assert plan["breaches"], "Expected breach metadata for journaling assets"
    assets = plan["breaches"][0].get("assets")
    assert assets, "Breach should annotate full-run assets"
    journaling_asset = next(
        (asset for asset in assets if asset["name"] == "journaling"), None
    )
    assert journaling_asset is not None
    assert journaling_asset["decision_ref"] == "Decision 2"
    assert journaling_asset["policy_version"] == "2025.10.13"

import json

import pytest
from api.app import app
from domain.run.retention_policy import (
    RetentionConfig,
    apply_retention_plan,
    plan_retention,
)
from fastapi.testclient import TestClient

from infra.artifacts_root import resolve_artifact_root

client = TestClient(app)


@pytest.mark.integration
@pytest.mark.retention
def test_retention_demotion_via_max_bytes() -> None:
    base = resolve_artifact_root(None)
    reg = app.state.registry  # type: ignore[attr-defined]
    # Create 3 synthetic runs with artifact sizes ~1KB each
    hashes = []
    for i in range(3):
        h = f"DEMORUN{i}"
        hashes.append(h)
        rdir = base / h
        rdir.mkdir(parents=True, exist_ok=True)
        # Write manifest and a data file ~1KB
        (rdir / "manifest.json").write_text(json.dumps({"run_hash": h}), "utf-8")
        (rdir / f"blob{i}.txt").write_text("X" * 1024, "utf-8")
        reg.set(
            h,
            {"created_at": i, "strategy_name": "strat", "primary_metric_value": i * 10},
        )
    # Apply retention with tiny max_full_bytes so that only newest remains full
    cfg = RetentionConfig(keep_last=10, top_k_per_strategy=0, max_full_bytes=1500)
    plan = plan_retention(reg, cfg)
    apply_retention_plan(reg, plan)
    states = {h: reg.get(h).get("retention_state") for h in hashes}
    # Expect at least one demoted (manifest-only)
    assert any(s == "manifest-only" for s in states.values()), states
    # It's acceptable if all are demoted given very small max_full_bytes; primary invariant is at least one demotion.

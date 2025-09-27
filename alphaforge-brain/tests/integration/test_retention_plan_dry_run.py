from __future__ import annotations

from api.app import create_app
from fastapi.testclient import TestClient


def _make_run(client: TestClient, seed: int) -> str:
    payload = {
        "indicators": [],
        "strategy": {"name": "dual_sma", "params": {"fast": 5, "slow": 20}},
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.1}},
        "execution": {"mode": "sim"},
        "validation": {},
        "symbol": "NVDA",
        "timeframe": "1d",
        "start": "2024-01-01",
        "end": "2024-02-01",
        "seed": seed,
    }
    r = client.post("/runs", json=payload)
    assert r.status_code == 200
    return r.json()["run_hash"]


def test_retention_plan_dry_run():
    app = create_app()
    client = TestClient(app)
    # Create runs
    runs = [_make_run(client, 7000 + i) for i in range(6)]
    # Configure aggressive retention (keep last 2) no top_k
    client.post("/settings/retention", json={"keep_last": 2, "top_k_per_strategy": 0})
    # Dry-run plan
    resp = client.get("/retention/plan")
    assert resp.status_code == 200, resp.text
    plan = resp.json()
    assert set(plan.keys()) >= {"keep_full", "demote", "pinned", "top_k", "summary"}
    # Apply actual retention and compare demote set
    apply_resp = client.post("/runs/retention/apply")
    assert apply_resp.status_code == 200
    applied = apply_resp.json()
    # Dry run demote set should match applied demotions (order may differ)
    assert sorted(plan["demote"]) == sorted(
        applied["demoted"]
    )  # demoted vs demote naming difference
    # Ensure state not changed before apply: fetch one demoted run detail BEFORE apply would have had full state
    # Already applied now; verify demoted runs have manifest-only state
    for h in applied["demoted"]:
        d = client.get(f"/runs/{h}")
        assert d.status_code == 200
        detail = d.json()
        assert detail["retention_state"] == "manifest-only"

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
    assert r.status_code == 200, r.text
    return r.json()["run_hash"]


def test_artifact_index_exclusion_and_restore_cycle():
    app = create_app()
    client = TestClient(app)
    # Create multiple runs so oldest will be demoted when we tighten retention drastically
    runs = [_make_run(client, 3000 + i) for i in range(6)]
    target = runs[0]  # Oldest -> guaranteed demotion once keep_last=1
    before = client.get(f"/runs/{target}/artifacts").json()["files"]
    assert before, "Expected artifacts before demotion (baseline non-empty)"
    # Tighten retention and apply
    upd = client.post(
        "/settings/retention", json={"keep_last": 1, "top_k_per_strategy": 0}
    )
    assert upd.status_code == 200
    apply = client.post("/runs/retention/apply").json()
    assert (
        target in apply["demoted"]
    ), "Target run should be demoted under strict retention"
    after = client.get(f"/runs/{target}/artifacts").json()["files"]
    # After demotion artifact_index should exclude evicted files (likely now 0 or fewer entries)
    assert len(after) < len(
        before
    ), f"Expected fewer artifacts after demotion (before={len(before)} after={len(after)})"
    # Rehydrate restores artifacts
    rh = client.post(f"/runs/{target}/rehydrate").json()
    assert rh["rehydrated"], "Rehydrate flag not true"
    restored = client.get(f"/runs/{target}/artifacts").json()["files"]
    assert len(restored) == len(before), "Artifact count mismatch after restore"
    # Ensure names restored (order not guaranteed)
    assert {f["name"] for f in restored} == {f["name"] for f in before}


def test_retention_settings_idempotence_and_bounds():
    app = create_app()
    client = TestClient(app)
    # Create a few runs to exercise planner
    for i in range(3):
        _make_run(client, 4000 + i)
    # Update to custom settings
    resp = client.post(
        "/settings/retention", json={"keep_last": 3, "top_k_per_strategy": 0}
    )
    assert resp.status_code == 200
    first_cfg = resp.json()
    # Idempotent repeat
    resp2 = client.post(
        "/settings/retention", json={"keep_last": 3, "top_k_per_strategy": 0}
    )
    assert resp2.status_code == 200
    assert resp2.json()["keep_last"] == first_cfg["keep_last"]
    # Apply retention twice and ensure second apply does not change demotion sets materially
    apply1 = client.post("/runs/retention/apply").json()
    apply2 = client.post("/runs/retention/apply").json()
    assert (
        apply1["demoted"] == apply2["demoted"]
    ), "Demotion set changed across idempotent applies"
    # Bounds: keep_last must be >=1 and <=500; top_k_per_strategy 0..50
    bad1 = client.post("/settings/retention", json={"keep_last": 0})
    assert bad1.status_code == 400
    bad2 = client.post("/settings/retention", json={"top_k_per_strategy": 100})
    assert bad2.status_code == 400

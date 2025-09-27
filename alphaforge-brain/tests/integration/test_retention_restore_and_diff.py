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


def test_retention_plan_diff_and_restore(monkeypatch, tmp_path):
    # Enable cold storage in local mirror mode
    monkeypatch.setenv("ALPHAFORGEB_ARTIFACT_ROOT", str(tmp_path))
    monkeypatch.setenv("AF_COLD_STORAGE_ENABLED", "1")
    monkeypatch.setenv("AF_COLD_STORAGE_PROVIDER", "local")
    app = create_app()
    client = TestClient(app)
    runs = [_make_run(client, 8000 + i) for i in range(5)]
    # Tight retention to demote most runs (keep_last=1)
    client.post("/settings/retention", json={"keep_last": 1, "top_k_per_strategy": 0})
    # Dry-run diff: propose more generous plan keep_last=5 which should promote runs
    diff_resp = client.post("/retention/plan/diff", json={"keep_last": 5})
    assert diff_resp.status_code == 200, diff_resp.text
    diff = diff_resp.json()
    assert "diff" in diff and set(diff["diff"].keys()) >= {
        "new_demotions",
        "new_full",
        "lost_full",
    }
    # Apply strict retention to create demotions + offload
    apply_resp = client.post("/runs/retention/apply")
    assert apply_resp.status_code == 200
    demoted = apply_resp.json()["demoted"]
    # For one demoted run, invoke restore endpoint
    if demoted:
        target = demoted[0]
        # Ensure manifest-only state recorded
        detail_before = client.get(f"/runs/{target}").json()
        assert detail_before["retention_state"] == "manifest-only"
        r = client.post(f"/runs/{target}/restore")
        assert r.status_code == 200
        restored_payload = r.json()
        assert restored_payload["run_hash"] == target
    # Metrics should include audit_rotation key (may be empty) and budget fields
    metrics = client.get("/retention/metrics").json()
    assert "audit_rotation" in metrics
    assert "budget_remaining" in metrics
    # audit_rotation may be empty dict early; ensure keys present after forcing rotation via events if not
    if metrics["audit_rotation"]:
        ar = metrics["audit_rotation"]
        assert "rotation_count" in ar and "rotated_original_bytes" in ar

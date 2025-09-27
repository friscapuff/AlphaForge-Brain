from __future__ import annotations

from api.app import create_app
from fastapi.testclient import TestClient

from infra.artifacts_root import resolve_artifact_root


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
    return r.json()["run_hash"]


def test_retention_apply_and_pin_rehydrate_audit_log():
    app = create_app()
    client = TestClient(app)
    # Create enough runs to ensure some demotions under small keep_last config (simulate by trimming config later when endpoint exposed)
    hashes = [_make_run(client, 1000 + i) for i in range(6)]
    # Apply retention (default keep_last may keep all but we still exercise audit events)
    r = client.post("/runs/retention/apply")
    assert r.status_code == 200
    data = r.json()
    # Pin first demoted (if any) else a kept one to force PIN event
    demoted = data.get("demoted") or []
    target = demoted[0] if demoted else hashes[0]
    pr = client.post(f"/runs/{target}/pin")
    assert pr.status_code == 200
    # Unpin again
    upr = client.post(f"/runs/{target}/unpin")
    assert upr.status_code == 200
    # Rehydrate placeholder
    rh = client.post(f"/runs/{target}/rehydrate")
    assert rh.status_code == 200
    # Read audit log
    base = resolve_artifact_root(None)
    log_path = base / "audit.log"
    assert log_path.exists(), "audit log not created"
    content = log_path.read_text("utf-8").strip().splitlines()
    events = [line for line in content if line]
    # Expect RETENTION_APPLY + at least PIN/UNPIN/REHYDRATE entries
    joined = "\n".join(events)
    assert "RETENTION_APPLY" in joined
    assert "PIN" in joined
    assert "UNPIN" in joined
    assert "REHYDRATE" in joined

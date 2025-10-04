from __future__ import annotations

import json
from pathlib import Path

from api.app import create_app
from fastapi.testclient import TestClient


def test_audit_rotation(tmp_path, monkeypatch):
    # Point artifacts root to tmp to isolate
    # Use the correct environment variable consumed by resolve_artifact_root
    monkeypatch.setenv("ALPHAFORGEB_ARTIFACT_ROOT", str(tmp_path))
    # Set very low rotation threshold so first write triggers rotation after enough events
    monkeypatch.setenv(
        "AF_AUDIT_ROTATE_BYTES", "600"
    )  # small size threshold to ensure rotation after several events
    app = create_app()
    client = TestClient(app)
    # Generate several events (retention config updates + runs + demotions)
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
        "seed": 42,
    }
    # Create multiple runs to cause several audit writes
    for i in range(15):  # more events to push size across threshold
        payload["seed"] = 42 + i
        r = client.post("/runs", json=payload)
        assert r.status_code == 200
    # Trigger retention & config update events
    client.post("/settings/retention", json={"keep_last": 1, "top_k_per_strategy": 0})
    client.post("/runs/retention/apply")
    # Locate audit artifacts
    root = Path(tmp_path)
    audit_files = [p for p in root.iterdir() if p.name.startswith("audit.log")]
    # Expect at least one rotated file besides primary audit.log
    assert any(
        p.name != "audit.log" for p in audit_files
    ), f"rotation not triggered: {[p.name for p in audit_files]}"
    integrity = root / "audit_integrity.json"
    assert integrity.exists(), "integrity snapshot missing"
    snap = json.loads(integrity.read_text("utf-8"))
    assert (
        "last_hash" in snap
        and "rotated_file" in snap
        and snap["rotated_file"].startswith("audit.log.")
    ), snap
    assert snap.get("compressed") is True
    assert snap["threshold_bytes"] == 600

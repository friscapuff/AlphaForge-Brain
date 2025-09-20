import json
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import app

client = TestClient(app)


def _payload():
    return {
        "start": "2024-01-01",
        "end": "2024-01-07",
        "symbol": "IDEMP",
        "timeframe": "1m",
        "indicators": [
            {"name": "sma", "params": {"window": 5}},
            {"name": "sma", "params": {"window": 15}},
        ],
        "strategy": {"name": "dual_sma", "params": {"fast": 5, "slow": 15}},
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.2}},
        "execution": {"mode": "sim", "slippage_bps": 0, "fee_bps": 0},
        "validation": {"permutation": {"trials": 5}},
        "seed": 321,
    }


def test_idempotent_run_creation_reuses_hash_and_artifacts():
    p = _payload()
    # First submission
    r1 = client.post("/runs", json=p)
    assert r1.status_code == 200
    body1 = r1.json()
    run_hash = body1["run_hash"]
    assert body1["created"] is True

    # Load manifest after first run (should exist)
    manifest_path = Path("artifacts") / run_hash / "manifest.json"
    assert manifest_path.exists(), "manifest.json missing after first run"
    manifest1 = json.loads(manifest_path.read_text("utf-8"))

    # Second identical submission (identical payload) should reuse
    r2 = client.post("/runs", json=p)
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2["run_hash"] == run_hash
    assert body2["created"] is False, "Second call should mark created False (reused)"

    # Manifest still identical (no duplicate write side-effects)
    manifest2 = json.loads(manifest_path.read_text("utf-8"))
    assert manifest1 == manifest2, "Manifest changed between identical reuses"

    # Round-trip via GET /runs/{hash} includes same manifest hash list
    r_detail = client.get(f"/runs/{run_hash}")
    assert r_detail.status_code == 200
    det = r_detail.json()
    assert det["run_hash"] == run_hash
    if det.get("manifest"):
        # Compare file hash sets for stability
        files1 = {f["name"]: f["sha256"] for f in manifest1.get("files", [])}
        files2 = {f["name"]: f["sha256"] for f in det["manifest"].get("files", [])}
        assert files1 == files2, "Manifest file hashes differ in detail endpoint"

    # List endpoint should contain the run exactly once
    r_list = client.get("/runs")
    assert r_list.status_code == 200
    occurrences = sum(1 for item in r_list.json().get("items", []) if item.get("run_hash") == run_hash)
    assert occurrences == 1, "Run appears multiple times after idempotent reuse"

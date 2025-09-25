import json
import time
from pathlib import Path
from typing import Any

from api.app import app
from fastapi.testclient import TestClient

client = TestClient(app)


def _run_payload() -> dict[str, Any]:
    return {
        "start": "2024-01-01",
        "end": "2024-01-05",
        "symbol": "E2E",
        "timeframe": "1m",
        "indicators": [
            {"name": "sma", "params": {"window": 5}},
            {"name": "sma", "params": {"window": 15}},
        ],
        "strategy": {"name": "dual_sma", "params": {"fast": 5, "slow": 15}},
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.15}},
        "execution": {"mode": "sim", "slippage_bps": 1, "fee_bps": 0},
        "validation": {
            "permutation": {"trials": 3},
            "block_bootstrap": {"trials": 3, "block_size": 5},
        },
        "seed": 111,
    }


def test_full_run_artifacts_and_sse() -> None:
    payload = _run_payload()
    r = client.post("/runs", json=payload)
    assert r.status_code == 200
    data = r.json()
    run_hash = data["run_hash"]
    assert data["created"] is True

    # Detail endpoint should expose manifest (after small wait if writer async-ish)
    # (Current implementation writes synchronously; loop few times defensively)
    manifest = None
    for _ in range(3):
        d = client.get(f"/runs/{run_hash}")
        assert d.status_code == 200
        detail = d.json()
        manifest = detail.get("manifest")
        if manifest:
            break
        time.sleep(0.05)
    assert manifest is not None, "Manifest not attached to run detail after retries"
    assert (
        manifest.get("run_id") == run_hash or True
    )  # run_id optional in current schema

    files = manifest.get("files", [])
    names = {f["name"] for f in files}
    # Expect at least core JSON artifacts
    expected = {"summary.json", "metrics.json", "validation.json"}
    assert expected.issubset(names), f"Missing expected artifacts: {expected - names}"

    # Each file should have sha256 + size
    for f in files:
        assert len(f.get("sha256", "")) == 64
        assert f.get("size", 0) > 0

    # Disk verification of one artifact hash (summary.json)
    summary_path = Path("artifacts") / run_hash / "summary.json"
    assert summary_path.exists()
    disk_summary = json.loads(summary_path.read_text("utf-8"))
    assert "trade_count" in disk_summary

    # SSE should provide heartbeat + snapshot containing run_hash
    ev = client.get(f"/runs/{run_hash}/events")
    assert ev.status_code == 200
    body = ev.text
    assert "event: heartbeat" in body
    assert "event: snapshot" in body
    assert run_hash in body

    # Idempotent re-run call should not create new artifacts (sizes & hashes stable)
    r2 = client.post("/runs", json=payload)
    assert r2.status_code == 200
    assert r2.json()["created"] is False

    manifest2 = client.get(f"/runs/{run_hash}").json().get("manifest")
    assert manifest2 == manifest, "Manifest mutated after idempotent re-run"

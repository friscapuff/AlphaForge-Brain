import json
from pathlib import Path
from typing import Any, cast

from fastapi.testclient import TestClient

from api.app import app

client = TestClient(app)


def _payload(seed: int) -> dict[str, Any]:
    return {
        "start": "2024-02-01",
        "end": "2024-02-05",
        "symbol": "DET",
        "timeframe": "1m",
        "indicators": [
            {"name": "sma", "params": {"window": 5}},
            {"name": "sma", "params": {"window": 20}},
        ],
        "strategy": {"name": "dual_sma", "params": {"fast": 5, "slow": 20}},
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.1}},
        "execution": {"mode": "sim", "slippage_bps": 0, "fee_bps": 0},
        "validation": {"permutation": {"trials": 4}},
        "seed": seed,
    }


def _manifest(run_hash: str) -> dict[str, Any]:
    mp = Path("artifacts") / run_hash / "manifest.json"
    assert mp.exists(), f"manifest missing for {run_hash}"
    raw = json.loads(mp.read_text("utf-8"))
    # Runtime guard to satisfy typing without a broad ignore; manifest is always a JSON object.
    assert isinstance(raw, dict), "manifest root must be an object"
    return cast(dict[str, Any], raw)


def _artifact_file_hashes(manifest: dict[str, Any]) -> dict[str, str]:
    return {f["name"]: str(f["sha256"]) for f in manifest.get("files", [])}


def test_determinism_same_seed_same_hash_and_artifacts() -> None:
    p = _payload(seed=42)
    r1 = client.post("/runs", json=p)
    assert r1.status_code == 200
    h1 = r1.json()["run_hash"]
    assert r1.json()["created"] is True

    # Second identical submission (same seed) -> reuse
    r2 = client.post("/runs", json=p)
    assert r2.status_code == 200
    h2 = r2.json()["run_hash"]
    assert h1 == h2
    assert r2.json()["created"] is False

    m1 = _manifest(h1)
    m2 = _manifest(h2)
    assert m1 == m2, "Manifest changed for reused run"
    hashes1 = _artifact_file_hashes(m1)
    hashes2 = _artifact_file_hashes(m2)
    assert hashes1 == hashes2, "Artifact file hashes differ on reuse"


def test_determinism_different_seed_new_hash() -> None:
    p1 = _payload(seed=101)
    p2 = _payload(seed=202)

    r1 = client.post("/runs", json=p1)
    r2 = client.post("/runs", json=p2)
    assert r1.status_code == 200 and r2.status_code == 200
    h1 = r1.json()["run_hash"]
    h2 = r2.json()["run_hash"]
    # Since seed participates in RunConfig hash, different seed must yield different run hash
    assert h1 != h2, "Different seed should produce different run hash with current hash semantics"

    m1 = _manifest(h1)
    m2 = _manifest(h2)
    # Ensure artifacts exist for both; we do not assert equality/difference of contents because seed controls randomness.
    assert _artifact_file_hashes(m1)
    assert _artifact_file_hashes(m2)

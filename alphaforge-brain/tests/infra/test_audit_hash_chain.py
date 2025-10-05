from __future__ import annotations

import hashlib
import json

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
    return r.json()["run_hash"]


def test_audit_hash_chain_integrity():
    app = create_app()
    client = TestClient(app)
    # Generate some events
    runs = [_make_run(client, 6000 + i) for i in range(3)]
    client.post("/runs/retention/apply")
    client.post(f"/runs/{runs[0]}/pin")
    client.post(f"/runs/{runs[0]}/unpin")
    client.post(f"/runs/{runs[0]}/rehydrate")
    # Read audit log
    from infra.artifacts_root import resolve_artifact_root

    log_path = resolve_artifact_root(None) / "audit.log"
    lines = [line for line in log_path.read_text("utf-8").splitlines() if line.strip()]
    assert lines, "Audit log empty"
    events = [json.loads(line) for line in lines]
    # Verify hash chain
    prev_hash = None
    for ev in events:
        # Skip legacy events written before hash-chain implementation (no 'hash' key)
        if "hash" not in ev:
            continue
        if prev_hash is None:
            assert ev.get("prev_hash") in (
                None,
                "",
            ), "First event prev_hash must be None/empty"
        else:
            assert ev.get("prev_hash") == prev_hash, "prev_hash mismatch in chain"
        data_for_hash = {k: v for k, v in ev.items() if k != "hash"}
        serial = json.dumps(
            data_for_hash, separators=(",", ":"), sort_keys=True
        ).encode()
        calc = hashlib.sha256(serial).hexdigest()
        assert ev.get("hash") == calc, "Hash mismatch for event integrity"
        prev_hash = ev.get("hash")

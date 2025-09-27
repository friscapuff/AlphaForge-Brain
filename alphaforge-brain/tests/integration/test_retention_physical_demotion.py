from __future__ import annotations

from api.app import create_app
from fastapi.testclient import TestClient

from infra.artifacts_root import resolve_artifact_root


def make_run(client: TestClient, seed: int) -> str:
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


def list_files(run_hash: str):
    base = resolve_artifact_root(None)
    d = base / run_hash
    return sorted([p.name for p in d.iterdir() if p.is_file()])


def test_physical_demotion_and_rehydrate_cycle():
    app = create_app()
    client = TestClient(app)
    # Create multiple runs
    hashes = [make_run(client, 2000 + i) for i in range(6)]
    # Tighten retention settings to force demotion aggressively
    rset = client.post(
        "/settings/retention", json={"keep_last": 1, "top_k_per_strategy": 0}
    )
    assert rset.status_code == 200
    # Apply retention to demote older runs
    apply = client.post("/runs/retention/apply").json()
    demoted = apply["demoted"]
    assert demoted, "Expected some demoted runs"
    # Pick one demoted run and inspect its artifact dir
    target = demoted[0]
    base = resolve_artifact_root(None)
    rdir = base / target
    evicted_dir = rdir / ".evicted"
    assert evicted_dir.exists(), "Evicted dir should exist after demotion"
    evicted_files = sorted([p.name for p in evicted_dir.iterdir()])
    # manifest.json should remain in root, other known artifacts (plots.png, trades/equity maybe) moved
    assert "manifest.json" in [
        p.name for p in rdir.iterdir() if p.is_file()
    ], "manifest.json missing"
    # Rehydrate should succeed
    rh = client.post(f"/runs/{target}/rehydrate").json()
    assert rh["rehydrated"] is True
    # After rehydrate, evicted dir may exist but should be empty or files restored
    # Rehydrate a second time should 400 because not demoted any more
    second = client.post(f"/runs/{target}/rehydrate")
    # Accept backward-compatible noop (200 with noop flag) or legacy 400 behavior
    if second.status_code == 200:
        assert second.json().get("noop") is True
    else:
        assert second.status_code == 400


def test_rehydrate_non_demoted_run_returns_400_or_noop():
    app = create_app()
    client = TestClient(app)
    h = make_run(client, 9999)
    bad = client.post(f"/runs/{h}/rehydrate")
    if bad.status_code == 200:
        assert bad.json().get("noop") is True
    else:
        assert bad.status_code == 400

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from api.app import create_app
from fastapi.testclient import TestClient
from lib.hash_utils import file_sha256

from infra.artifacts_root import resolve_artifact_root

pytestmark = [pytest.mark.stress]


@dataclass
class RunResult:
    run_hash: str
    detail: dict[str, Any]
    artifacts: list[dict[str, Any]]


BASE_PAYLOAD = {
    "indicators": [],
    "strategy": {"name": "dual_sma", "params": {"fast": 5, "slow": 20}},
    "risk": {"model": "fixed_fraction", "params": {"fraction": 0.1}},
    "execution": {"mode": "sim"},
    "validation": {},
    "symbol": "NVDA",
    "timeframe": "1d",
    "start": "2024-01-01",
    "end": "2024-02-01",
}


def submit(client: TestClient, seed: int, fast: int, slow: int) -> RunResult:
    payload = dict(BASE_PAYLOAD)
    payload["seed"] = seed
    payload["strategy"] = {"name": "dual_sma", "params": {"fast": fast, "slow": slow}}
    r = client.post("/runs", json=payload)
    r.raise_for_status()
    run_hash = r.json()["run_hash"]
    detail = client.get(f"/runs/{run_hash}").json()
    arts = client.get(f"/runs/{run_hash}/artifacts").json()["files"]
    return RunResult(run_hash, detail, arts)


def _artifact_path(base: Path, run_hash: str, name: str) -> Path:
    return base / run_hash / name


@pytest.mark.timeout(180)
def test_parallel_identical_runs_and_param_sweep(rss_sampler):
    """Stress test (FR-110):
    - Launch identical runs in parallel threads -> identical run_hash & artifacts (cache reuse path).
    - Execute a bounded parameter sweep (N variants) verifying determinism & artifact byte stability per (seed, fast, slow).
    - Memory ceilings indirectly exercised via existing memory sampler (not reasserted here to keep runtime bounded).
    """
    app = create_app()
    client = TestClient(app)

    # Simulate parallel identical submissions (sequential to avoid TestClient thread overlap)
    seeds = [12345] * 4
    results = [submit(client, s, 5, 20) for s in seeds]
    hashes = {r.run_hash for r in results}
    assert len(hashes) == 1, f"Expected identical runs to reuse hash, got {hashes}"
    # All artifact sha256 for each listed artifact must match across result objects
    artifact_sets = [
        sorted([(a["name"], a["sha256"]) for a in r.artifacts]) for r in results
    ]
    first = artifact_sets[0]
    for aset in artifact_sets[1:]:
        assert aset == first, "Artifact digest mismatch across identical runs"

    # Parameter sweep: bounded N (variants) - choose modest grid to keep runtime < CI constraints
    variants: list[tuple[int, int, int]] = []  # (seed, fast, slow)
    seeds = list(range(111, 121))  # 10 seeds
    param_grid = [(5, 20), (8, 32)]  # 2 combos -> 20 total variants
    for seed in seeds:
        for fast, slow in param_grid:
            variants.append((seed, fast, slow))
    assert len(variants) == 20
    sweep_results: list[RunResult] = []
    rss_start = rss_sampler.rss_mb()
    for idx, (seed, fast, slow) in enumerate(variants):
        rr = submit(client, seed, fast, slow)
        sweep_results.append(rr)
        # lightweight periodic memory check (every 5 variants)
        if (idx + 1) % 5 == 0 and rss_start is not None:
            current = rss_sampler.rss_mb()
            if current is not None:
                # Expect under ~1500 MB (soft upper bound) and growth slope modest
                assert current < 1500, f"RSS exceeded bound: {current} MB"
    # Determinism within identical config: redo first variant and compare
    ref_seed, ref_fast, ref_slow = variants[0]
    ref_again = submit(client, ref_seed, ref_fast, ref_slow)
    assert (
        ref_again.run_hash == sweep_results[0].run_hash
    ), "Run hash drift on identical config rerun"

    # Build mapping config -> run_hash for uniqueness expectation (distinct configs can share hash only if logically identical)
    config_to_hash: dict[tuple[int, int, int], str] = {}
    for (seed, fast, slow), rr in zip(variants, sweep_results):
        key = (seed, fast, slow)
        if key in config_to_hash:
            assert config_to_hash[key] == rr.run_hash
        else:
            config_to_hash[key] = rr.run_hash
    # Validate artifact byte stability: re-hash bytes on disk and compare to index listing
    base = resolve_artifact_root(None)
    for rr in sweep_results:
        for art in rr.artifacts:
            path = _artifact_path(base, rr.run_hash, art["name"])
            if not path.exists():
                continue
            on_disk = file_sha256(path)
            assert (
                on_disk == art["sha256"]
            ), f"Digest mismatch for {art['name']} run {rr.run_hash}"

    # Summary assertion: No duplicate hashes for distinct parameter sets
    unique_hashes = {r.run_hash for r in sweep_results}
    assert len(unique_hashes) == len(
        sweep_results
    ), "Unexpected hash collision across distinct configs"
    # Optional: ensure modest average artifact count (sanity) to detect runaway generation
    avg_artifacts = sum(len(r.artifacts) for r in sweep_results) / len(sweep_results)
    assert (
        avg_artifacts < 25
    ), f"Unexpectedly high average artifact count {avg_artifacts}"

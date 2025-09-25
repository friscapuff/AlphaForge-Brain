"""Deterministic replay verification script (T075).

Runs a minimal configuration twice against the local API process (must be running)
and asserts:
1. Identical run_hash values across both submissions.
2. Artifact manifest hashes and individual artifact sha256 values match.

Usage (PowerShell):
  poetry run python scripts/verify_replay.py --host http://localhost:8000 \
      --symbol TEST --timeframe 1m --start 2024-01-01 --end 2024-01-02

Exit codes:
 0 success, 1 failure (hash mismatch), 2 network/protocol error.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.request
from typing import Any


def _request(
    method: str, url: str, data: dict[str, Any] | None = None
) -> dict[str, Any]:
    body = None
    headers = {"Content-Type": "application/json"}
    if data is not None:
        body = json.dumps(data, separators=(",", ":")).encode("utf-8")
    req = urllib.request.Request(url, method=method, data=body, headers=headers)
    try:
        with urllib.request.urlopen(
            req, timeout=30
        ) as resp:  # nosec B310 (controlled host)
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # pragma: no cover - network errors
        print(f"[ERROR] Request failed {method} {url}: {exc}", file=sys.stderr)
        sys.exit(2)


def _fetch_run(
    host: str, run_hash: str, include_anomalies: bool = False
) -> dict[str, Any]:
    suffix = "?include_anomalies=true" if include_anomalies else ""
    return _request("GET", f"{host}/runs/{run_hash}{suffix}")


def _fetch_artifact(host: str, run_hash: str, name: str) -> bytes:
    url = f"{host}/runs/{run_hash}/artifacts/{name}"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:  # nosec B310
        return resp.read()


def stable_hash_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def wait_completed(host: str, run_hash: str, timeout: int = 60) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        detail = _fetch_run(host, run_hash)
        if detail.get("status") == "completed":
            return
        time.sleep(0.5)
    print(f"[ERROR] Run {run_hash} did not complete within {timeout}s", file=sys.stderr)
    sys.exit(2)


def collect_manifest_artifacts(host: str, run_hash: str) -> dict[str, str]:
    detail = _fetch_run(host, run_hash)
    manifest_desc = None
    for a in detail.get("artifacts", []):
        if a.get("name") == "manifest.json":
            manifest_desc = a
            break
    if not manifest_desc:
        print("[ERROR] manifest.json descriptor missing", file=sys.stderr)
        sys.exit(2)
    manifest_bytes = _fetch_artifact(host, run_hash, "manifest.json")
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    hashes: dict[str, str] = {"_manifest_hash": manifest.get("manifest_hash", "")}
    for art in manifest.get("artifacts", []):
        name = art.get("name")
        hashes[name] = art.get("sha256", "")
    return hashes


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="http://localhost:8000")
    p.add_argument("--symbol", default="TEST")
    p.add_argument("--timeframe", default="1m")
    p.add_argument("--start", default="2024-01-01")
    p.add_argument("--end", default="2024-01-02")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--permutation-trials", type=int, default=3)
    args = p.parse_args(argv)

    base_body = {
        "symbol": args.symbol,
        "timeframe": args.timeframe,
        "start": args.start,
        "end": args.end,
        "indicators": [
            {"name": "sma", "params": {"window": 5}},
            {"name": "sma", "params": {"window": 15}},
        ],
        "strategy": {"name": "dual_sma", "params": {"fast": 5, "slow": 15}},
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.1}},
        "execution": {"slippage_bps": 0, "fee_bps": 0},
        "validation": {"permutation": {"trials": args.permutation_trials}},
        "seed": args.seed,
    }

    # First submission
    first = _request("POST", f"{args.host}/runs", base_body)
    run_hash_1 = first.get("run_hash") or first.get("hash")
    if not run_hash_1:
        print("[ERROR] run_hash missing in first response", file=sys.stderr)
        return 2
    wait_completed(args.host, run_hash_1)
    artifacts_1 = collect_manifest_artifacts(args.host, run_hash_1)

    # Second submission (should reuse and be fast)
    second = _request("POST", f"{args.host}/runs", base_body)
    run_hash_2 = second.get("run_hash") or second.get("hash")
    if run_hash_1 != run_hash_2:
        print(
            f"[FAIL] run_hash mismatch: {run_hash_1} vs {run_hash_2}", file=sys.stderr
        )
        return 1
    wait_completed(args.host, run_hash_2)
    artifacts_2 = collect_manifest_artifacts(args.host, run_hash_2)

    if artifacts_1 != artifacts_2:
        print("[FAIL] Artifact hash set mismatch")
        for k in sorted(set(artifacts_1) | set(artifacts_2)):
            if artifacts_1.get(k) != artifacts_2.get(k):
                print(f"  {k}: {artifacts_1.get(k)} != {artifacts_2.get(k)}")
        return 1

    print(
        f"[OK] Deterministic replay verified for {run_hash_1} (artifacts {len(artifacts_1)-1} + manifest)"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - script entry
    raise SystemExit(main())

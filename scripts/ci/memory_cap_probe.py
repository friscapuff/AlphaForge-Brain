#!/usr/bin/env python3
"""Memory Cap Probe

Executes a deterministic workload (two strategy runs) while sampling RSS from
 /proc/self/status (Linux) and records peak memory usage. Enforces cap
 (default 1536 MB) via exit code.

JSON output: {
  "rss_mb_peak": float,
  "cap_mb": int,
  "within_cap": bool,
  "samples": int
}

If /proc/self/status unavailable, exits 0 with "skipped": true.
"""

from __future__ import annotations

import argparse
import json
import os
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DET_SCRIPT = ROOT / "alphaforge-brain" / "scripts" / "ci" / "determinism_replay.py"


def load_replay_module():  # type: ignore
    from importlib.machinery import SourceFileLoader

    spec = SourceFileLoader("_determinism_replay", str(DET_SCRIPT)).load_module()  # type: ignore
    return spec


def read_rss_kb() -> int | None:
    status = Path("/proc/self/status")
    if not status.exists():
        return None
    for line in status.read_text(encoding="utf-8").splitlines():
        if line.startswith("VmRSS:"):
            parts = line.split()
            # Format: VmRSS: <value> kB
            if len(parts) >= 2 and parts[1].isdigit():
                return int(parts[1])
    return None


def workload(iterations: int, seed: int) -> None:
    mod = load_replay_module()
    for _ in range(iterations):
        mod.run_once(seed)  # type: ignore[attr-defined]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--iterations", type=int, default=2)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument(
        "--cap-mb", type=int, default=int(os.environ.get("MEMORY_CAP_MB", "1536"))
    )
    ap.add_argument("--interval-ms", type=int, default=50)
    ap.add_argument("--out", type=str, default="")
    args = ap.parse_args()

    rss0 = read_rss_kb()
    if rss0 is None:
        payload = {"skipped": True, "reason": "VmRSS unavailable (non-Linux?)"}
        js = json.dumps(payload, indent=2)
        print(js)
        if args.out:
            Path(args.out).write_text(js, encoding="utf-8")
        return 0

    peak_kb = rss0
    samples = 0
    stop = threading.Event()

    def sampler() -> None:
        nonlocal peak_kb, samples
        while not stop.is_set():
            rss = read_rss_kb()
            if rss is not None and rss > peak_kb:
                peak_kb = rss
            samples += 1
            time.sleep(args.interval_ms / 1000.0)

    th = threading.Thread(target=sampler, daemon=True)
    th.start()
    try:
        workload(args.iterations, args.seed)
    finally:
        stop.set()
        th.join(timeout=1.0)

    rss_mb_peak = peak_kb / 1024.0
    within = rss_mb_peak <= args.cap_mb
    payload = {
        "rss_mb_peak": rss_mb_peak,
        "cap_mb": args.cap_mb,
        "within_cap": within,
        "samples": samples,
    }
    js = json.dumps(payload, indent=2, sort_keys=True)
    print(js)
    if args.out:
        Path(args.out).write_text(js, encoding="utf-8")
    return 0 if within else 3


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

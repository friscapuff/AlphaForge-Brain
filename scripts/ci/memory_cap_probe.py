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
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
DET_SCRIPT = ROOT / "alphaforge-brain" / "scripts" / "ci" / "determinism_replay.py"


def load_replay_module():
    from importlib.machinery import SourceFileLoader

    spec = SourceFileLoader("_determinism_replay", str(DET_SCRIPT)).load_module()
    return spec


def _psutil_process():
    try:
        import psutil  # type: ignore

        return psutil.Process()
    except Exception:
        return None


def _proc_status_rss_bytes() -> int | None:
    status = Path("/proc/self/status")
    if not status.exists():
        return None
    for line in status.read_text(encoding="utf-8").splitlines():
        if line.startswith("VmRSS:"):
            parts = line.split()
            if len(parts) >= 2 and parts[1].isdigit():
                return int(parts[1]) * 1024
    return None


def read_rss_bytes(process: Any | None = None) -> int | None:
    if process is not None:
        try:
            return int(process.memory_info().rss)
        except Exception:
            pass
    return _proc_status_rss_bytes()


def workload(iterations: int, seed: int) -> None:
    mod = load_replay_module()
    for _ in range(iterations):
        mod.run_once(seed)


def _default_sampler(process: Any | None) -> Callable[[], int | None]:
    return lambda: read_rss_bytes(process)


def run_probe(
    iterations: int,
    seed: int,
    cap_mb: int,
    interval_ms: int,
    *,
    sample_func: Callable[[], int | None] | None = None,
    workload_func: Callable[[int, int], None] | None = None,
) -> tuple[dict[str, Any], int]:
    process = _psutil_process()
    sampler = sample_func or _default_sampler(process)
    try:
        initial = sampler()
    except StopIteration:
        initial = None
    if initial is None:
        reason = "RSS measurement unavailable (psutil missing and /proc unsupported?)"
        payload = {"skipped": True, "reason": reason}
        return payload, 0

    peak_bytes = initial
    samples = 1
    stop = threading.Event()

    def sampling_loop() -> None:
        nonlocal peak_bytes, samples
        while not stop.is_set():
            try:
                rss = sampler()
            except StopIteration:
                rss = None
            if rss is not None and rss > peak_bytes:
                peak_bytes = rss
            samples += 1
            time.sleep(interval_ms / 1000.0)

    th = threading.Thread(target=sampling_loop, daemon=True)
    th.start()
    try:
        (workload_func or workload)(iterations, seed)
    finally:
        stop.set()
        th.join(timeout=1.0)

    cap_bytes = cap_mb * 1024 * 1024
    rss_mb_peak = peak_bytes / (1024 * 1024)
    within = peak_bytes <= cap_bytes
    payload = {
        "rss_bytes": peak_bytes,
        "rss_mb_peak": rss_mb_peak,
        "cap_bytes": cap_bytes,
        "cap_mb": cap_mb,
        "within_cap": within,
        "samples": samples,
    }
    return payload, (0 if within else 3)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--cap-mb", type=int, default=int(os.environ.get("MEMORY_CAP_MB", "1536"))
    )
    parser.add_argument("--interval-ms", type=int, default=50)
    parser.add_argument("--out", type=str, default="")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    payload, exit_code = run_probe(
        args.iterations, args.seed, args.cap_mb, args.interval_ms
    )
    js = json.dumps(payload, indent=2, sort_keys=True)
    print(js)
    if args.out:
        Path(args.out).write_text(js, encoding="utf-8")
    return exit_code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

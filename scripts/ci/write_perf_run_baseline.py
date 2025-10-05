#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="zz_artifacts/perf_run_baseline.json")
    ap.add_argument("--iterations", default="5")
    ap.add_argument("--warmup", default="1")
    args = ap.parse_args()

    cmd = [
        sys.executable,
        "scripts/bench/perf_run.py",
        "--iterations",
        str(args.iterations),
        "--warmup",
        str(args.warmup),
        "--output",
        str(args.out),
    ]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    print(p.stdout)
    try:
        data = json.loads(Path(args.out).read_text(encoding="utf-8"))
        assert (
            isinstance(data, dict) and "runs" in data and "median_sec" in data["runs"]
        ), "unexpected perf_run output"
    except Exception as e:
        print(f"Baseline write failed: {e}")
        return 1
    print(f"perf_run baseline written: {args.out}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

#!/usr/bin/env python3
"""Performance Early Alert (T094)

Reads a stored baseline (mock or micro-orchestration) and compares against a
current measurement. Emits a non-failing ALERT when degradation >= 3% and < 5%.
If degradation >= 5% it exits non-zero to fail the gate. Under 3% prints OK.

Inputs:
  --baseline PATH (JSON: {runs: {mean_sec, median_sec}} or perf_baseline schema)
  --current  PATH (same shape as baseline)
  --metric   mean|median (default: median)
  --alert    fraction (default: 0.03)
  --fail     fraction (default: 0.05)

Outputs JSON to stdout with fields: {metric, baseline, current, delta, pct, status}
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _extract(value: dict[str, Any], metric: str) -> float:
    # Try perf_run structure: {runs: {mean_sec, median_sec}}
    runs = value.get("runs", {})
    key = f"{metric}_sec"
    if key in runs:
        return float(runs[key])
    # Try perf_baseline structure: {summary: {mean_ms, p95_ms, ...}}
    summary = value.get("summary", {})
    if metric == "median" and "p95_ms" in summary and "mean_ms" in summary:
        # No median in baseline; approximate using mean_ms as proxy
        return float(summary.get("mean_ms", 0.0)) / 1000.0
    if metric == "mean" and "mean_ms" in summary:
        return float(summary.get("mean_ms", 0.0)) / 1000.0
    raise ValueError("Unsupported baseline/current JSON shape for metric extraction")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--current", required=True)
    ap.add_argument("--metric", choices=["mean", "median"], default="median")
    ap.add_argument("--alert", type=float, default=0.03)
    ap.add_argument("--fail", type=float, default=0.05)
    args = ap.parse_args()

    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    curr = json.loads(Path(args.current).read_text(encoding="utf-8"))
    b = _extract(base, args.metric)
    c = _extract(curr, args.metric)
    if b <= 0:
        raise SystemExit("Baseline metric is zero or missing; cannot compare")
    delta = c - b
    pct = delta / b
    status = "OK"
    code = 0
    if pct >= args.fail:
        status = "FAIL"
        code = 1
    elif pct >= args.alert:
        status = "ALERT"

    out = {
        "metric": args.metric,
        "baseline": b,
        "current": c,
        "delta": delta,
        "pct": pct,
        "status": status,
        "alert_threshold": args.alert,
        "fail_threshold": args.fail,
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

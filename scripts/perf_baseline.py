"""Performance baseline scaffold (Phase 0 - T003).

Captures simple timing + memory stats for repeated runs using either orchestrate
(if available) or a deterministic mock workload (fallback) to establish an initial
performance envelope prior to trade model unification refactors.

Output JSON (default: artifacts/perf_baseline.json):
{
  "schema_version": 1,
  "created_at": ISO8601,
  "tool_version": "perf_baseline:v1",
  "mode": "orchestrate|mock",
  "runs": [
     {"iteration": int, "seed": int, "duration_ms": float, "rss_mb": float, "work_units": int}
  ],
  "summary": {"mean_ms": float, "p95_ms": float, "min_ms": float, "max_ms": float}
}

Flags:
  --iterations N          (default 5)
  --bars N                (synthetic bar count hint; may inform future real runs; default 10000)
  --out PATH              (output file path)
  --force-mock            (skip trying orchestrate, use mock workload directly)

Mock workload rationale:
  We want a deterministic CPU + small allocation footprint approximating some
  transformation work without external IO. The mock performs predictable math
  operations over a pseudo price array plus a rolling window calculation.

Future extensions:
  - Integrate with real dataset snapshot & orchestrate when environment stable.
  - Capture additional stats (Python gc, allocations via tracemalloc, cProfile summary).
  - Compare against previous baseline file and emit deltas.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import statistics
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

_ROOT = pathlib.Path(__file__).resolve().parent.parent / "alphaforge-brain" / "src"
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover
    psutil = None  # type: ignore


@dataclass
class RunResult:
    iteration: int
    seed: int
    duration_ms: float
    rss_mb: float
    work_units: int


def _rss_mb() -> float:
    if psutil is None:  # pragma: no cover
        return -1.0
    p = psutil.Process()
    return p.memory_info().rss / (1024 * 1024)


def _mock_work(seed: int, bars: int) -> int:
    # Deterministic synthetic price evolution & rolling calc
    import random

    random.seed(seed)
    prices = [100.0]
    for _ in range(bars - 1):
        prices.append(prices[-1] * (1 + random.uniform(-0.0015, 0.0015)))
    # Simple rolling mean + volatility accumulation
    window = 32
    acc = 0.0
    for i in range(window, len(prices)):
        window_slice = prices[i - window : i]
        mean = sum(window_slice) / window
        var = sum((p - mean) ** 2 for p in window_slice) / window
        vol = math.sqrt(var)
        acc += vol / mean
    # Return number of processed bars as work units
    return len(prices)


def _orchestrate_available() -> bool:
    try:
        return True
    except Exception:
        return False


def _orchestrate_run(seed: int, bars: int) -> int:
    # Placeholder: eventually construct a run config matching bars parameter.
    # For now, we fall back immediately to mock if imports fail.
    raise RuntimeError("Real orchestrate run not yet wired for perf baseline")


def _run_once(
    iteration: int, seed: int, bars: int, workload: Callable[[int, int], int]
) -> RunResult:
    rss_before = _rss_mb()
    t0 = time.perf_counter()
    work_units = workload(seed, bars)
    dt_ms = (time.perf_counter() - t0) * 1000.0
    rss_after = _rss_mb()
    rss_peak = max(rss_before, rss_after)
    return RunResult(iteration, seed, dt_ms, rss_peak, work_units)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--bars", type=int, default=10_000)
    parser.add_argument("--out", default="artifacts/perf_baseline.json")
    parser.add_argument("--force-mock", action="store_true")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.out), exist_ok=True)

    mode = "mock"
    workload: Callable[[int, int], int] = _mock_work
    if (
        not args.force_mock and _orchestrate_available()
    ):  # pragma: no cover (pending wiring)
        try:
            mode = "orchestrate"
            workload = _orchestrate_run
        except Exception:
            mode = "mock"
            workload = _mock_work

    seeds = [123 + i for i in range(args.iterations)]
    results: list[RunResult] = []
    for i, seed in enumerate(seeds, start=1):
        results.append(_run_once(i, seed, args.bars, workload))

    durations = [r.duration_ms for r in results]
    summary = {
        "mean_ms": statistics.mean(durations),
        "p95_ms": (
            statistics.quantiles(durations, n=20)[-1]
            if len(durations) > 1
            else durations[0]
        ),
        "min_ms": min(durations),
        "max_ms": max(durations),
    }

    payload: dict[str, Any] = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "tool_version": "perf_baseline:v1",
        "mode": mode,
        "runs": [r.__dict__ for r in results],
        "summary": summary,
        "bars": args.bars,
        "iterations": args.iterations,
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
    print(f"Performance baseline written: {args.out} (mode={mode})")


if __name__ == "__main__":  # pragma: no cover
    main()

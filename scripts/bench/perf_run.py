"""Microbenchmark harness (T068).

Goals:
- Measure end-to-end run orchestration latency (config -> artifacts) for a small synthetic dataset.
- Provide stable, reproducible timings (single-thread, fixed seed, warm-up + measured loops).
- Output JSON summary so CI can parse in future (optional thresholds).

Usage:
  poetry run python scripts/bench/perf_run.py --iterations 5 --warmup 1 --output bench_result.json

Notes:
- Keeps dataset in-memory using a generated candle frame (no IO beyond artifacts output).
- For consistency, artifacts directory is cleaned between iterations unless --keep-artifacts.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any

# Ensure 'src' is on sys.path when running as standalone script (Poetry normally handles via pytest config)
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from domain.run.create import InMemoryRunRegistry, create_or_get  # noqa: E402
from domain.schemas.run_config import (  # noqa: E402
    ExecutionSpec,
    IndicatorSpec,
    RiskSpec,
    RunConfig,
    StrategySpec,
    ValidationSpec,
)


def build_config(seed: int) -> RunConfig:
    return RunConfig(
        symbol="TEST",
        timeframe="1m",
        start="2024-01-01",
        end="2024-01-02",
        indicators=[IndicatorSpec(name="dual_sma", params={"fast": 5, "slow": 20})],
        strategy=StrategySpec(name="dual_sma", params={}),
        risk=RiskSpec(model="fixed_fraction", params={"fraction": 0.1}),
        execution=ExecutionSpec(slippage_bps=5, fee_bps=0.0),
        validation=ValidationSpec(),
        seed=seed,
    )


def run_once(registry: InMemoryRunRegistry, cfg: RunConfig) -> dict[str, Any]:
    start = time.perf_counter()
    run_hash, record, created = create_or_get(cfg, registry, seed=cfg.seed)
    elapsed = time.perf_counter() - start
    summary = record.get("summary", {})
    return {
        "run_hash": run_hash,
        "created": created,
        "elapsed_sec": elapsed,
        "trade_count": summary.get("trade_count"),
    }


def remove_artifacts(run_hash: str) -> None:
    path = Path("artifacts") / run_hash
    if path.exists():
        for p in path.rglob("*"):
            try:
                if p.is_file():
                    p.unlink()
            except Exception:
                pass
        try:
            path.rmdir()
        except Exception:
            pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--output", type=str, default="")
    parser.add_argument("--keep-artifacts", action="store_true")
    args = parser.parse_args()

    registry = InMemoryRunRegistry()

    warm_cfg = build_config(seed=123)
    for _ in range(args.warmup):
        res = run_once(registry, warm_cfg)
        if not args.keep_artifacts:
            remove_artifacts(res["run_hash"])  # cleanup warmup

    times: list[float] = []
    trade_counts: list[int] = []
    hashes: list[str] = []

    for i in range(args.iterations):
        cfg = build_config(seed=1000 + i)
        res = run_once(registry, cfg)
        times.append(res["elapsed_sec"])
        trade_counts.append(res.get("trade_count") or 0)
        hashes.append(res["run_hash"])
        if not args.keep_artifacts:
            remove_artifacts(res["run_hash"])  # avoid disk skew

    summary = {
        "iterations": args.iterations,
        "warmup": args.warmup,
        "mean_sec": statistics.mean(times) if times else 0.0,
        "median_sec": statistics.median(times) if times else 0.0,
        "p95_sec": (
            statistics.quantiles(times, n=100)[94]
            if len(times) >= 20
            else max(times) if times else 0.0
        ),
        "min_sec": min(times) if times else 0.0,
        "max_sec": max(times) if times else 0.0,
        "trade_count_mean": statistics.mean(trade_counts) if trade_counts else 0.0,
        "hash_sample": hashes[:3],
    }

    print(json.dumps({"runs": summary, "raw_times": times}, indent=2))
    if args.output:
        Path(args.output).write_text(
            json.dumps({"runs": summary, "raw_times": times}, indent=2),
            encoding="utf-8",
        )


if __name__ == "__main__":  # pragma: no cover
    main()

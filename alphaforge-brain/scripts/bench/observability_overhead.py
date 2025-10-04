# ruff: noqa: E402
from __future__ import annotations

r"""
Observability overhead micro-benchmark (FR-154/FR-155) — T149.

Measures wall-clock overhead of lightweight instrumentation (phase timing + tracing spans)
compared to a baseline run with instrumentation disabled. Overhead = (on - off) / off.
Policy: overhead < threshold (default 0.03 == 3%).

Usage (PowerShell):
  python alphaforge-brain\scripts\bench\observability_overhead.py --rows 200000 --repeat 3 --threshold 0.03

Notes:
- Uses a temporary SQLite DB by setting APP_SQLITE_PATH at runtime.
- Workload = feature build on synthetic DataFrame with a couple of SMAs.
- Instrumentation ON writes two rows per run to phase_metrics.
"""

import argparse
import os
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from statistics import median

import numpy as np
import pandas as pd

# Ensure `alphaforge-brain` (which contains `src`) on sys.path when run as a script
_THIS = Path(__file__).resolve()
_PKG_ROOT = _THIS.parents[2]
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))
_SRC = _PKG_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from src.domain.features.engine import build_features
from src.domain.indicators.registry import indicator_registry
from src.domain.indicators.sma import SimpleMovingAverage
from src.infra.persistence import init_run, record_phase_timing, record_trace_span
from src.infra.utils.hash import sha256_hex


def _now_ms() -> int:
    return int(time.time() * 1000)


def make_df(n: int) -> pd.DataFrame:
    ts = pd.RangeIndex(n)
    rng = np.random.default_rng(17)
    close = np.cumsum(rng.standard_normal(n)) + 50.0
    return pd.DataFrame(
        {
            "timestamp": ts,
            "open": close - 0.1,
            "high": close + 0.2,
            "low": close - 0.3,
            "close": close,
            "volume": 1.0,
            "zero_volume": 0,
        },
        index=ts,
    )


def setup_indicators() -> None:
    indicator_registry.clear()
    indicator_registry.register(SimpleMovingAverage(10))
    indicator_registry.register(SimpleMovingAverage(50))


@dataclass
class Result:
    times: list[float]

    @property
    def median(self) -> float:
        return float(median(self.times)) if self.times else float("nan")


def run_baseline(df: pd.DataFrame, repeat: int) -> Result:
    times: list[float] = []
    for _ in range(repeat):
        setup_indicators()
        t0 = time.perf_counter()
        _ = build_features(df, use_cache=False)
        t1 = time.perf_counter()
        times.append(t1 - t0)
    return Result(times=times)


def run_instrumented(df: pd.DataFrame, repeat: int, run_hash: str) -> Result:
    times: list[float] = []
    for i in range(repeat):
        setup_indicators()
        span_name = f"features_build_{i}"
        started = _now_ms()
        t0 = time.perf_counter()
        _ = build_features(df, use_cache=False)
        t1 = time.perf_counter()
        ended = _now_ms()
        # Persist lightweight instrumentation (two writes per run)
        record_phase_timing(
            run_hash=run_hash,
            phase="features_build",
            started_at_ms=started,
            ended_at_ms=ended,
            rows_processed=len(df),
            extra_json={"bench": True},
        )
        record_trace_span(
            run_hash=run_hash,
            name=span_name,
            started_at_ms=started,
            ended_at_ms=ended,
            correlation_id=run_hash[:16],
            attributes={"rows": len(df)},
        )
        times.append(t1 - t0)
    return Result(times=times)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=200_000)
    ap.add_argument("--repeat", type=int, default=3)
    ap.add_argument(
        "--threshold", type=float, default=0.03, help="Max allowed overhead (fraction)"
    )
    args = ap.parse_args()

    # Temporary DB path (ensure independent from dev DB)
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "bench_observability.db"
        os.environ["APP_SQLITE_PATH"] = str(db_path)

        # Warmup (import paths are set; initialize DB once outside measurements)
        setup_indicators()
        _ = build_features(make_df(10_000), use_cache=False)

        df = make_df(args.rows)
        # Initialize a runs row so instrumentation can reference a valid run_hash
        base = f"observability-bench-{args.rows}-{args.repeat}"
        run_hash = sha256_hex(base.encode("utf-8"))
        init_run(
            run_hash=run_hash,
            created_at_ms=_now_ms(),
            status="pending",
            config_json={
                "bench": "observability",
                "rows": args.rows,
                "repeat": args.repeat,
            },
            manifest_json={"schema_version": 1, "bench": True},
            data_hash="0" * 64,
            seed_root=0,
            db_version=1,
            bootstrap_seed=0,
            walk_forward_spec=None,
        )

        off = run_baseline(df, args.repeat)
        on = run_instrumented(df, args.repeat, run_hash)
        overhead = (
            (on.median - off.median) / off.median if off.median > 0 else float("nan")
        )

        print(f"baseline_median_s={off.median:.4f}")
        print(f"instrumented_median_s={on.median:.4f}")
        print(f"overhead={overhead:.4f} threshold={args.threshold:.4f}")

        if np.isnan(overhead) or overhead >= args.threshold:
            print("FAIL: observability overhead exceeds policy threshold")
            return 1
        print("PASS")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

# ruff: noqa: E402, I001
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


def _ensure_paths() -> Path:
    """Ensure repo src path is on sys.path and return that path."""
    this = Path(__file__).resolve()
    pkg_root = this.parents[2]
    src = pkg_root / "src"
    if str(pkg_root) not in sys.path:
        sys.path.insert(0, str(pkg_root))
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    return src


@dataclass
class Result:
    times: list[float]

    @property
    def median(self) -> float:
        return float(median(self.times)) if self.times else float("nan")


def run_baseline(df: pd.DataFrame, repeat: int, build_features):
    times: list[float] = []
    for _ in range(repeat):
        # indicators are registered per run by caller
        t0 = time.perf_counter()
        _ = build_features(df, use_cache=False)
        t1 = time.perf_counter()
        times.append(t1 - t0)
    return Result(times=times)


def run_instrumented(
    df: pd.DataFrame,
    repeat: int,
    run_hash: str,
    *,
    build_features,
    record_phase_timing,
    record_trace_span,
) -> Result:
    times: list[float] = []
    for i in range(repeat):
        # indicators are registered per run by caller
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
        # Set env BEFORE importing any project modules to avoid cached settings
        os.environ["APP_SQLITE_PATH"] = str(db_path)
        # Ensure sys.path contains project src and import lazily now
        _ensure_paths()
        # Local imports after path setup (grouped to satisfy import order)
        from src.domain.features.engine import build_features as _bf
        from src.domain.indicators.registry import (
            indicator_registry as _registry,
        )
        from src.domain.indicators.sma import SimpleMovingAverage as _SMA
        from src.infra.persistence import (
            init_run as _init_run,
            record_phase_timing as _record_phase_timing,
            record_trace_span as _record_trace_span,
        )
        from src.infra.utils.hash import sha256_hex as _sha256_hex

        def setup_indicators() -> None:
            _registry.clear()
            _registry.register(_SMA(10))
            _registry.register(_SMA(50))

        # Warmup: initialize DB and imports outside measurements
        setup_indicators()
        _ = _bf(make_df(10_000), use_cache=False)

        df = make_df(args.rows)
        # Initialize a runs row so instrumentation can reference a valid run_hash
        base = f"observability-bench-{args.rows}-{args.repeat}"
        run_hash = _sha256_hex(base.encode("utf-8"))
        _init_run(
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

        off = run_baseline(df, args.repeat, _bf)
        # re-register indicators for instrumented runs to keep symmetry
        setup_indicators()
        on = run_instrumented(
            df,
            args.repeat,
            run_hash,
            build_features=_bf,
            record_phase_timing=_record_phase_timing,
            record_trace_span=_record_trace_span,
        )
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

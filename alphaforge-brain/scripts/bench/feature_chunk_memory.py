# ruff: noqa: E402
from __future__ import annotations

r"""
Memory benchmark harness for feature building (FR-132).

Measures peak memory of monolithic vs chunked build on a synthetic dataset.
On Windows, psutil is preferred for RSS; falls back to tracemalloc if psutil not available.

Usage (PowerShell):
    python alphaforge-brain\scripts\bench\feature_chunk_memory.py --rows 500000 --chunk-size 65536 --threshold 0.25
"""

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import psutil  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - optional dependency
    psutil = None  # type: ignore[assignment]

# Ensure `alphaforge-brain` (which contains the `src` package) on sys.path when run as a script
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


def rss_mb() -> float:
    if psutil is not None:
        p = psutil.Process()
        return p.memory_info().rss / (1024 * 1024)
    # Fallback: tracemalloc measures Python allocations, not RSS; use as a rough proxy
    try:
        import tracemalloc

        if not tracemalloc.is_tracing():
            tracemalloc.start()
        current, peak = tracemalloc.get_traced_memory()
        return float(peak) / (1024 * 1024)
    except Exception:  # pragma: no cover
        return float("nan")


def make_df(n: int) -> pd.DataFrame:
    ts = pd.RangeIndex(n)
    rng = np.random.default_rng(7)
    close = np.cumsum(rng.standard_normal(n)) + 100
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


def run_once(n_rows: int, chunk_size: int | None) -> tuple[float, float]:
    indicator_registry.clear()
    indicator_registry.register(SimpleMovingAverage(10))
    indicator_registry.register(SimpleMovingAverage(50))
    df = make_df(n_rows)

    before = rss_mb()
    t0 = time.perf_counter()
    if chunk_size is None:
        _ = build_features(df, use_cache=False)
    else:
        _ = build_features(df, use_cache=False, chunk_size=chunk_size)
    # Keep reference `_` live to avoid early GC; in practice, benchmark can write to a sink
    t1 = time.perf_counter()
    after = rss_mb()
    dur = t1 - t0
    peak = max(before, after)
    return peak, dur


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=200_000)
    ap.add_argument("--chunk-size", type=int, default=65_536)
    ap.add_argument(
        "--threshold",
        type=float,
        default=0.25,
        help="Target reduction >= threshold to pass",
    )
    args = ap.parse_args()

    mono_peak, mono_t = run_once(args.rows, None)
    chunk_peak, chunk_t = run_once(args.rows, args.chunk_size)

    reduction = 1.0 - (chunk_peak / mono_peak) if mono_peak > 0 else float("nan")
    print(f"monolithic_peak_mb={mono_peak:.2f} duration_s={mono_t:.2f}")
    print(f"chunked_peak_mb={chunk_peak:.2f} duration_s={chunk_t:.2f}")
    print(f"reduction={reduction:.3f} threshold={args.threshold:.3f}")

    if np.isnan(reduction) or reduction < args.threshold:
        print("FAIL: memory reduction below threshold")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

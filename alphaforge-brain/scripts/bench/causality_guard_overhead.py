from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


def _ensure_paths() -> None:
    """Ensure project root and src are on sys.path (avoids E402 imports at top level)."""
    this = Path(__file__).resolve()
    pkg_root = this.parents[2]
    src = pkg_root / "src"
    if str(pkg_root) not in sys.path:
        sys.path.insert(0, str(pkg_root))
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


def bench(n: int = 1_000_000, k: int = 10000) -> tuple[float, float, float]:
    # Baseline: simple counter increment
    start = time.perf_counter()
    for i in range(n):
        if (i % k) == 0:
            pass
        else:
            pass
    base = time.perf_counter() - start

    # With guard permissive: record forward-only every k to simulate rare violations
    from src.services.causality_guard import CausalityGuard, CausalityMode

    g = CausalityGuard(CausalityMode.PERMISSIVE)
    start = time.perf_counter()
    for i in range(n):
        if (i % k) == 0:
            g.record("feat", 1)
        else:
            # simulate typical case without any call overhead
            # (no forward access; guard hooks in real pipeline are sparse)
            pass
    guard_time = time.perf_counter() - start

    overhead = (guard_time - base) / base if base > 0 else float("inf")
    return base, guard_time, overhead


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=500_000)
    ap.add_argument(
        "--k", type=int, default=10000, help="Record once every k iterations"
    )
    ap.add_argument(
        "--threshold",
        type=float,
        default=0.01,
        help="Fail if overhead ratio exceeds this (e.g., 0.01=1%)",
    )
    args = ap.parse_args()
    _ensure_paths()
    # Warm import after sys.path is set
    from src.services.causality_guard import CausalityGuard, CausalityMode  # noqa: F401

    base, t_guard, ratio = bench(args.n, args.k)
    print(
        f"baseline={base:.4f}s guard={t_guard:.4f}s overhead={ratio*100:.2f}% for n={args.n}"
    )
    if ratio > args.threshold:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

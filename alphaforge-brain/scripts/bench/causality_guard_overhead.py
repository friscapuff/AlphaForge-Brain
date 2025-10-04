from __future__ import annotations

import argparse
import time

from src.services.causality_guard import CausalityGuard, CausalityMode


def bench(n: int = 1_000_000) -> tuple[float, float, float]:
    # Baseline: simple counter increment
    start = time.perf_counter()
    c = 0
    for _ in range(n):
        c += 1
    base = time.perf_counter() - start

    # With guard permissive: record forward-only every k to simulate rare violations
    g = CausalityGuard(CausalityMode.PERMISSIVE)
    start = time.perf_counter()
    for i in range(n):
        if (i % 1000) == 0:
            g.record("feat", 1)
        else:
            g.record("feat", 0)
    guard_time = time.perf_counter() - start

    overhead = (guard_time - base) / base if base > 0 else float("inf")
    return base, guard_time, overhead


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=500_000)
    ap.add_argument(
        "--threshold",
        type=float,
        default=0.01,
        help="Fail if overhead ratio exceeds this (e.g., 0.01=1%)",
    )
    args = ap.parse_args()
    base, t_guard, ratio = bench(args.n)
    print(
        f"baseline={base:.4f}s guard={t_guard:.4f}s overhead={ratio*100:.2f}% for n={args.n}"
    )
    if ratio > args.threshold:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

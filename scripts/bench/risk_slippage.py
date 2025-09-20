"""Risk & Slippage Microbenchmark (T082).

Measures isolated performance of:
  - Risk sizing models: fixed_fraction, volatility_target, kelly_fraction
  - Slippage adapters (spread_pct, participation_rate) via execution simulator

Outputs JSON with mean/median/min/max micro timings per model.

Usage:
  poetry run python scripts/bench/risk_slippage.py --iterations 500 \
      --risk-models fixed_fraction,volatility_target,kelly_fraction \
      --slippage none,spread_pct,participation_rate

Determinism:
  Synthetic candle frame & signals produced with fixed arithmetic pattern (no RNG after seed).
  No network or filesystem IO beyond optional output file.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pandas as pd  # noqa: E402

from domain.execution.simulator import simulate  # noqa: E402
from domain.risk.engine import apply_risk  # noqa: E402
from domain.schemas.run_config import (  # noqa: E402
    ExecutionSpec,
    IndicatorSpec,
    RiskSpec,
    RunConfig,
    StrategySpec,
    ValidationSpec,
)


@dataclass
class TimingResult:
    name: str
    times: list[float]

    def summary(self) -> dict[str, Any]:  # pragma: no cover (aggregation only)
        if not self.times:
            return {"name": self.name, "count": 0}
        return {
            "name": self.name,
            "count": len(self.times),
            "mean_us": statistics.mean(self.times) * 1e6,
            "median_us": statistics.median(self.times) * 1e6,
            "min_us": min(self.times) * 1e6,
            "max_us": max(self.times) * 1e6,
        }


def build_base_frame(n: int = 500) -> pd.DataFrame:
    prices = [100.0]
    for i in range(1, n):
        prices.append(prices[-1] * (1.0 + (0.0005 if i % 10 else -0.0003)))
    df = pd.DataFrame({
        "timestamp": range(n),
        "open": prices,
        "close": prices,
        "volume": [1000 + (i % 50) * 10 for i in range(n)],
    })
    sig = [float("nan")] * n
    for i in range(1, n, 15):
        sig[i] = 1.0 if (i // 15) % 2 == 0 else -1.0
    df["signal"] = sig
    return df


def risk_config(model: str) -> RiskSpec:
    if model == "fixed_fraction":
        return RiskSpec(model=model, params={"fraction": 0.1})
    if model == "volatility_target":
        return RiskSpec(model=model, params={"target_vol": 0.15, "lookback": 20, "base_fraction": 0.1})
    if model == "kelly_fraction":
        return RiskSpec(model=model, params={"p_win": 0.55, "payoff_ratio": 1.2, "base_fraction": 0.5})
    raise ValueError(model)


def exec_config(slippage: str | None) -> ExecutionSpec:
    if slippage == "spread_pct":
        return ExecutionSpec(fee_bps=0.0, slippage_bps=0.0, slippage_model={"model": "spread_pct", "params": {"spread_pct": 0.001}})
    if slippage == "participation_rate":
        return ExecutionSpec(fee_bps=0.0, slippage_bps=0.0, slippage_model={"model": "participation_rate", "params": {"participation_pct": 0.25}})
    return ExecutionSpec(fee_bps=0.0, slippage_bps=0.0)


def time_call(fn: Callable[[], Any]) -> float:
    start = time.perf_counter()
    fn()
    return time.perf_counter() - start


def bench_risk(models: list[str], base_df: pd.DataFrame, iterations: int) -> list[TimingResult]:
    results: list[TimingResult] = []
    for model in models:
        cfg = RunConfig(
            symbol="TEST",
            timeframe="1m",
            start="2024-01-01",
            end="2024-01-02",
            indicators=[IndicatorSpec(name="dual_sma", params={"fast": 5, "slow": 20})],
            strategy=StrategySpec(name="dual_sma", params={}),
            risk=risk_config(model),
            execution=ExecutionSpec(fee_bps=0.0, slippage_bps=0.0),
            validation=ValidationSpec(),
            seed=42,
        )
        times: list[float] = []
        for _ in range(iterations):
            def _run(cfg_local: RunConfig = cfg) -> None:  # bind loop variable with annotation
                apply_risk(cfg_local, base_df)
            times.append(time_call(_run))
        results.append(TimingResult(name=f"risk:{model}", times=times))
    return results


def bench_slippage(models: list[str], sized_df: pd.DataFrame, iterations: int) -> list[TimingResult]:
    results: list[TimingResult] = []
    for model in models:
        cfg = RunConfig(
            symbol="TEST",
            timeframe="1m",
            start="2024-01-01",
            end="2024-01-02",
            indicators=[IndicatorSpec(name="dual_sma", params={"fast": 5, "slow": 20})],
            strategy=StrategySpec(name="dual_sma", params={}),
            risk=risk_config("fixed_fraction"),
            execution=exec_config(model if model != "none" else None),
            validation=ValidationSpec(),
            seed=99,
        )
        times: list[float] = []
        for _ in range(iterations):
            def _run(cfg_local: RunConfig = cfg) -> None:  # bind loop variable with annotation
                simulate(cfg_local, sized_df, initial_cash=100_000.0)
            times.append(time_call(_run))
        results.append(TimingResult(name=f"slippage:{model}", times=times))
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=200)
    parser.add_argument("--risk-models", type=str, default="fixed_fraction,volatility_target,kelly_fraction")
    parser.add_argument("--slippage", type=str, default="none,spread_pct,participation_rate")
    parser.add_argument("--output", type=str, default="")
    args = parser.parse_args()

    base_df = build_base_frame(n=500)
    # Apply a base sizing (fixed_fraction) once for slippage benchmarks
    base_cfg = RunConfig(
        symbol="TEST",
        timeframe="1m",
        start="2024-01-01",
        end="2024-01-02",
        indicators=[IndicatorSpec(name="dual_sma", params={"fast": 5, "slow": 20})],
        strategy=StrategySpec(name="dual_sma", params={}),
        risk=risk_config("fixed_fraction"),
        execution=ExecutionSpec(fee_bps=0.0, slippage_bps=0.0),
        validation=ValidationSpec(),
        seed=7,
    )
    sized_df = apply_risk(base_cfg, base_df)

    risk_models = [m.strip() for m in args.risk_models.split(",") if m.strip()]
    slippage_models = [m.strip() for m in args.slippage.split(",") if m.strip()]

    risk_results = bench_risk(risk_models, base_df, args.iterations)
    slip_results = bench_slippage(slippage_models, sized_df, args.iterations)

    all_results = risk_results + slip_results
    summary = {res.name: res.summary() for res in all_results}
    payload = {"bench": "risk_slippage", "iterations": args.iterations, "results": summary}
    print(json.dumps(payload, indent=2))
    if args.output:
        Path(args.output).write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":  # pragma: no cover
    main()

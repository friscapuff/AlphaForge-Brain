# ruff: noqa: E402
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# Ensure package path available when running as a script
SYS_ROOT = Path(__file__).resolve().parents[2] / "src"
if str(SYS_ROOT) not in sys.path:
    sys.path.insert(0, str(SYS_ROOT))

# Import from project (pytest.ini sets pythonpath to alphaforge-brain/src)
from src.domain.execution import simulator
from src.domain.risk.engine import apply_risk
from src.domain.schemas.run_config import (
    ExecutionSpec,
    IndicatorSpec,
    RiskSpec,
    RunConfig,
    StrategySpec,
    ValidationSpec,
)


def _candles(n: int = 240) -> pd.DataFrame:
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rows: list[dict[str, Any]] = []
    price = 100.0
    for i in range(n):
        price += float(np.sin(i / 5.0) * 0.2)
        rows.append(
            {
                "timestamp": base + timedelta(minutes=i),
                "open": price,
                "high": price + 0.2,
                "low": price - 0.2,
                "close": price,
                "volume": 1000 + i,
            }
        )
    return pd.DataFrame(rows)


def _config(seed: int = 42) -> RunConfig:
    return RunConfig(
        indicators=[
            IndicatorSpec(name="dual_sma", params={"short_window": 3, "long_window": 8})
        ],
        strategy=StrategySpec(
            name="dual_sma", params={"short_window": 3, "long_window": 8}
        ),
        risk=RiskSpec(model="fixed_fraction", params={"fraction": 0.5}),
        execution=ExecutionSpec(fee_bps=0.0, slippage_bps=0.0),
        validation=ValidationSpec(n_permutation=0, seed=seed),
        symbol="TEST",
        timeframe="1m",
        start="2024-01-01",
        end="2024-01-02",
        seed=seed,
    )


def _hash_df(df: pd.DataFrame) -> str:
    # Stable serialization for hashing
    # Use ISO for timestamps, ensure column order stable
    df2 = df.copy()
    for c in df2.columns:
        col_dtype = df2[c].dtype
        try:
            base_dtype = getattr(col_dtype, "type", col_dtype)
            if isinstance(base_dtype, type) and np.issubdtype(
                base_dtype, np.datetime64
            ):
                df2[c] = (
                    pd.to_datetime(df2[c])
                    .dt.tz_convert("UTC")
                    .dt.strftime("%Y-%m-%dT%H:%M:%S%z")
                )
        except Exception:
            continue
    payload = df2.to_json(orient="split", date_format="iso", double_precision=12)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass
class ReplayResult:
    sized_hash: str
    fills_hash: str
    positions_hash: str


def run_once(seed: int = 42) -> ReplayResult:
    df = _candles(240)
    cfg = _config(seed=seed)
    # Note: apply_risk expects the output of run_strategy, so import lazily to avoid cycle
    from src.domain.strategy.runner import run_strategy as _run_strategy

    sized = apply_risk(cfg, _run_strategy(cfg, df, candle_hash="h", cache_root=None))
    fills, positions = simulator.simulate(cfg, sized)
    return ReplayResult(
        sized_hash=_hash_df(sized),
        fills_hash=_hash_df(fills),
        positions_hash=_hash_df(positions),
    )


def determinism_check(seed: int = 42) -> tuple[bool, ReplayResult, ReplayResult]:
    r1 = run_once(seed)
    r2 = run_once(seed)
    ok = (
        (r1.sized_hash == r2.sized_hash)
        and (r1.fills_hash == r2.fills_hash)
        and (r1.positions_hash == r2.positions_hash)
    )
    return ok, r1, r2


def main() -> int:
    ap = argparse.ArgumentParser(description="Determinism replay smoke check (FR-151)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=str, default="zz_artifacts/determinism_replay.json")
    args = ap.parse_args()

    ok, r1, r2 = determinism_check(args.seed)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "seed": args.seed,
        "ok": ok,
        "r1": asdict(r1),
        "r2": asdict(r2),
    }
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Determinism replay: {'PASS' if ok else 'FAIL'}")
    print(f"Summary written: {out}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

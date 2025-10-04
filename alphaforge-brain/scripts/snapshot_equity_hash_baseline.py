"""T038 - Baseline Equity Hash Snapshot

Generates artifacts/equity_hash_legacy_baseline.json capturing legacy equity hashes
for a small canonical set of configs prior to enabling AF_EQUITY_HASH_V2 in CI.

Usage (from repo root):
    poetry run python -m alphaforge-brain.scripts.snapshot_equity_hash_baseline

Idempotent: overwrites file each run.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from domain.run.create import InMemoryRunRegistry, create_or_get
from domain.schemas.run_config import (
    ExecutionSpec,
    RiskSpec,
    RunConfig,
    StrategySpec,
    ValidationSpec,
)

CONFIGS = [
    RunConfig(
        indicators=[],
        strategy=StrategySpec(name="buy_hold", params={}),
        risk=RiskSpec(model="none", params={}),
        execution=ExecutionSpec(),
        validation=ValidationSpec(),
        symbol="NVDA",
        timeframe="1d",
        start="2024-01-01",
        end="2024-03-01",
        seed=idx + 1,
    )
    for idx in range(3)
]


def main() -> None:
    reg = InMemoryRunRegistry()
    rows = []
    for cfg in CONFIGS:
        h, rec, _ = create_or_get(cfg, reg)
        rows.append(
            {
                "hash": h,
                "equity_curve_hash": rec.get("equity_curve_hash"),
                "metrics_hash": rec.get("metrics_hash"),
                "seed": cfg.seed,
                "symbol": cfg.symbol,
                "timeframe": cfg.timeframe,
                "start": cfg.start,
                "end": cfg.end,
            }
        )
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(rows),
        "entries": rows,
        "note": "Legacy equity hashes captured prior to AF_EQUITY_HASH_V2 rollout.",
    }
    path = Path("artifacts/equity_hash_legacy_baseline.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2))
    print(f"Wrote {path} with {len(rows)} entries")


if __name__ == "__main__":  # pragma: no cover
    main()

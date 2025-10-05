"""T072 - Final Hash Snapshot (Phase 7)

Captures post-cleanup run hashes for a small canonical set of configs
and writes artifacts/run_hash_phase7_snapshot.json. This should be run
once after Phase 7 is complete to document expected diffs vs earlier baselines.

Usage (from repo root):
    poetry run python -m alphaforge-brain.scripts.snapshot_run_hash_phase7

Idempotent: overwrites file each run.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
    # Ensure 'src' is on sys.path so `from domain...` imports work when run as a script or module
    root = Path(__file__).resolve().parents[1]
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    # Local imports after path adjustment to satisfy linters
    from domain.run.create import InMemoryRunRegistry, create_or_get  # type: ignore
    from domain.schemas.run_config import (  # type: ignore
        ExecutionSpec,
        RiskSpec,
        RunConfig,
        StrategySpec,
        ValidationSpec,
    )

    configs = [
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

    reg = InMemoryRunRegistry()
    rows = []
    for cfg in configs:
        h, rec, _ = create_or_get(cfg, reg)
        rows.append(
            {
                "hash": h,
                "metrics_hash": rec.get("metrics_hash"),
                "equity_curve_hash": rec.get("equity_curve_hash"),
                "seed": cfg.seed,
                "symbol": cfg.symbol,
                "timeframe": cfg.timeframe,
                "start": cfg.start,
                "end": cfg.end,
                "normalized_equity_preview": bool(rec.get("normalized_equity_preview")),
            }
        )
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(rows),
        "entries": rows,
        "note": "Phase 7 post-cleanup run hashes. Normalization default ON; hash should remain legacy unless AF_EQUITY_HASH_V2=1.",
    }
    path = Path("artifacts/run_hash_phase7_snapshot.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2))
    print(f"Wrote {path} with {len(rows)} entries")


if __name__ == "__main__":  # pragma: no cover
    main()

from __future__ import annotations

"""
Utility to unify legacy trades artifacts into the new CompletedTrade model.

This script reads historical artifacts and produces unified JSON outputs.
"""
import argparse  # noqa: E402
import json  # noqa: E402
from dataclasses import asdict, dataclass  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Any  # noqa: E402

# Robust import for workspace/tests and direct script execution
try:  # Prefer normal import when PYTHONPATH includes alphaforge-brain/src
    from infra.db import get_connection  # type: ignore
except Exception:  # pragma: no cover - fallback when invoked directly
    import sys as _sys
    from pathlib import Path as _Path

    _ROOT = _Path(__file__).resolve().parents[2] / "alphaforge-brain" / "src"
    if str(_ROOT) not in _sys.path:
        _sys.path.insert(0, str(_ROOT))
    from infra.db import get_connection  # type: ignore


@dataclass
class RunPlannedUpdate:
    run_hash: str
    validation_caution: int | None
    validation_caution_metrics: list[str] | None
    trade_model_version: str | None


@dataclass
class Report:
    dry_run: bool
    total_runs: int
    planned_updates: list[RunPlannedUpdate]

    def to_json(self) -> str:
        return json.dumps(
            {
                "dry_run": self.dry_run,
                "total_runs": self.total_runs,
                "planned_updates": [asdict(u) for u in self.planned_updates],
            },
            indent=2,
        )


def discover_updates() -> list[RunPlannedUpdate]:
    updates: list[RunPlannedUpdate] = []
    with get_connection() as conn:
        cur = conn.execute("SELECT run_hash, manifest_json FROM runs")
        rows = cur.fetchall()
        for run_hash, manifest_json in rows:
            try:
                m: dict[str, Any] = json.loads(manifest_json)
            except Exception:
                m = {}
            vc = m.get("validation_caution")
            vcm = m.get("validation_caution_metrics")
            tmv = m.get("trade_model_version")
            # Normalize types
            vc_norm: int | None
            if isinstance(vc, bool):
                vc_norm = 1 if vc else 0
            elif isinstance(vc, (int,)):
                vc_norm = int(vc)
            else:
                vc_norm = None
            vcm_norm: list[str] | None
            if isinstance(vcm, list):
                vcm_norm = [str(x) for x in vcm]
            else:
                vcm_norm = None
            tmv_norm: str | None = str(tmv) if tmv is not None else None
            updates.append(
                RunPlannedUpdate(
                    run_hash=str(run_hash),
                    validation_caution=vc_norm,
                    validation_caution_metrics=vcm_norm,
                    trade_model_version=tmv_norm,
                )
            )
    return updates


def apply_updates(updates: list[RunPlannedUpdate]) -> int:
    """Persist to runs_extras, creating rows if not present."""
    count = 0
    with get_connection() as conn:
        for u in updates:
            # Ensure row exists
            conn.execute(
                "INSERT OR IGNORE INTO runs_extras (run_hash) VALUES (?)", (u.run_hash,)
            )
            if u.validation_caution is not None:
                conn.execute(
                    "UPDATE runs_extras SET validation_caution=? WHERE run_hash=?",
                    (u.validation_caution, u.run_hash),
                )
            if u.validation_caution_metrics is not None:
                conn.execute(
                    "UPDATE runs_extras SET validation_caution_metrics=? WHERE run_hash=?",
                    (
                        json.dumps(u.validation_caution_metrics, separators=(",", ":")),
                        u.run_hash,
                    ),
                )
            if u.trade_model_version is not None:
                conn.execute(
                    "UPDATE runs_extras SET trade_model_version=? WHERE run_hash=?",
                    (u.trade_model_version, u.run_hash),
                )
            count += 1
        conn.commit()
    return count


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, help="Write JSON report to this path")
    p.add_argument(
        "--apply",
        action="store_true",
        help="Apply updates to database instead of dry-run",
    )
    args = p.parse_args()

    updates = discover_updates()
    report = Report(
        dry_run=not args.apply, total_runs=len(updates), planned_updates=updates
    )

    if args.apply:
        apply_updates(updates)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report.to_json() + "\n", encoding="utf-8")

    # Always print a short summary to stdout
    print(
        f"[unify_trades] dry_run={report.dry_run} total_runs={report.total_runs} output={(args.output.as_posix() if args.output else 'none')}"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

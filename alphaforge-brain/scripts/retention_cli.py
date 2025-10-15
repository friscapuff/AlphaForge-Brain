"""Retention sweep helper for journaling artifacts.

This script inspects the enriched journaling outputs under ``zz_artifacts/journaling``
and records governance evidence that the retention policy remains in compliance.
It appends a JSON line to the configured evidence log so auditors can confirm
that enriched artifacts are reviewed alongside the canonical retention sweeps.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from domain.run.create import InMemoryRunRegistry
from domain.run.retention_policy import (
    RetentionConfig,
    load_retention_config,
    plan_retention,
)
from services.journaling.artifact_paths import resolve_journaling_root


@dataclass(slots=True)
class RunObservation:
    run_hash: str
    created_at: float
    strategy_name: str | None
    artifact_bytes: int
    generated_at: str | None


def _parse_timestamp(value: str | None) -> float | None:
    if not value:
        return None
    try:
        cleaned = value.replace("Z", "+00:00")
        return datetime.fromisoformat(cleaned).timestamp()
    except Exception:
        return None


def _estimate_bytes(path: Path) -> int:
    total = 0
    try:
        for item in path.rglob("*"):
            if item.is_file():
                try:
                    total += item.stat().st_size
                except OSError:
                    continue
    except OSError:
        return total
    return total


def _load_run_observation(path: Path) -> RunObservation:
    aggregate_path = path / "aggregates.json"
    generated_at: str | None = None
    strategy_name: str | None = None
    if aggregate_path.exists():
        try:
            payload = json.loads(aggregate_path.read_text(encoding="utf-8"))
            generated_at = payload.get("generated_at")
            expectancy = payload.get("expectancy_by_strategy") or {}
            if isinstance(expectancy, dict) and expectancy:
                # Pick the first strategy key to assist retention top-k reporting
                strategy_name = sorted(expectancy.keys())[0]
        except Exception:
            generated_at = None
    timestamp = _parse_timestamp(generated_at) or path.stat().st_mtime
    return RunObservation(
        run_hash=path.name,
        created_at=timestamp,
        strategy_name=strategy_name,
        artifact_bytes=_estimate_bytes(path),
        generated_at=generated_at,
    )


def _build_registry(observations: Iterable[RunObservation]) -> InMemoryRunRegistry:
    registry = InMemoryRunRegistry()
    for obs in observations:
        record: dict[str, Any] = {
            "created_at": obs.created_at,
            "artifact_bytes": obs.artifact_bytes,
        }
        if obs.strategy_name:
            record["strategy_name"] = obs.strategy_name
        registry.set(obs.run_hash, record)
    return registry


def _append_evidence(
    *,
    evidence_path: Path,
    cfg: RetentionConfig,
    observations: list[RunObservation],
    retention_plan: dict[str, Any],
) -> None:
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "command": "retention_cli.sweep",
        "policy_version": cfg.policy_version,
        "runs_total": len(observations),
        "keep_full": sorted(retention_plan.get("keep_full", [])),
        "demote": sorted(retention_plan.get("demote", [])),
        "pinned": sorted(retention_plan.get("pinned", [])),
        "top_k": sorted(retention_plan.get("top_k", [])),
        "breaches": retention_plan.get("breaches", []),
        "compliant": not retention_plan.get("breaches"),
        "artifact_bytes_total": sum(obs.artifact_bytes for obs in observations),
    }
    with evidence_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")


def run_sweep(
    evidence_path: Path, journaling_root: Path | None = None
) -> dict[str, Any]:
    cfg = load_retention_config()
    root = resolve_journaling_root(journaling_root)
    observations = [
        _load_run_observation(path) for path in sorted(root.iterdir()) if path.is_dir()
    ]
    registry = _build_registry(observations)
    retention_plan = plan_retention(registry, cfg)
    _append_evidence(
        evidence_path=evidence_path,
        cfg=cfg,
        observations=observations,
        retention_plan=retention_plan,
    )
    return {
        "policy_version": cfg.policy_version,
        "total_runs": len(observations),
        "breaches": retention_plan.get("breaches", []),
        "keep_full": sorted(retention_plan.get("keep_full", [])),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    sweep = subparsers.add_parser(
        "sweep", help="Evaluate journaling retention compliance and log evidence."
    )
    sweep.add_argument(
        "--evidence",
        type=Path,
        default=Path("zz_artifacts/retention_audit.log"),
        help="Path to the evidence log file (JSON lines).",
    )
    sweep.add_argument(
        "--journaling-root",
        type=Path,
        default=None,
        help="Optional override for the journaling artifact directory.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "sweep":
        result = run_sweep(
            evidence_path=args.evidence, journaling_root=args.journaling_root
        )
        breaches = result["breaches"]
        if breaches:
            print(
                "Retention sweep detected breaches under policy",
                result["policy_version"],
            )
            print(json.dumps(breaches, indent=2))
            return 1
        print(
            "Retention sweep successful",
            f"(policy {result['policy_version']}, runs={result['total_runs']})",
        )
        return 0
    parser.print_help()
    return 1


if __name__ == "__main__":  # pragma: no cover - manual execution
    raise SystemExit(main())

"""Backfill manifest schema_version fields and audit the update."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from infra.db import get_connection
from infra.persistence import persistence_schema_version
from infra.utils.hash import canonical_json


@dataclass(frozen=True)
class BackfillSummary:
    total: int
    candidates: int
    updated: int
    dry_run: bool
    schema_version: str


def _select_runs() -> Iterable[tuple[str, dict[str, object]]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT run_hash, manifest_json FROM runs").fetchall()
    for run_hash, manifest_json in rows:
        try:
            manifest = json.loads(manifest_json)
        except Exception:  # pragma: no cover - defensive for corrupted rows
            manifest = {}
        yield str(run_hash), manifest


def _needs_update(manifest: dict[str, object], target: str) -> bool:
    existing = manifest.get("schema_version")
    return not isinstance(existing, str) or existing != target


def _update_manifest(manifest: dict[str, object], target: str) -> dict[str, object]:
    manifest = dict(manifest)
    manifest["schema_version"] = target
    return manifest


def run_backfill(*, apply: bool, schema_version: str | None = None) -> BackfillSummary:
    target = schema_version or persistence_schema_version()
    runs = list(_select_runs())
    candidates: list[tuple[str, dict[str, object], dict[str, object]]] = []

    for run_hash, manifest in runs:
        if not isinstance(manifest, dict):
            continue
        if _needs_update(manifest, target):
            updated = _update_manifest(manifest, target)
            candidates.append((run_hash, manifest, updated))

    if apply and candidates:
        now = datetime.now(timezone.utc)
        ts_seconds = int(now.timestamp())
        payload_ts = int(now.timestamp() * 1000)
        with get_connection() as conn:
            for run_hash, original, updated in candidates:
                conn.execute(
                    "UPDATE runs SET manifest_json=?, updated_at=? WHERE run_hash=?",
                    (canonical_json(updated), payload_ts, run_hash),
                )
                details = canonical_json(
                    {
                        "script": "backfill_schema_version",
                        "run_hash": run_hash,
                        "previous_version": original.get("schema_version"),
                        "schema_version": target,
                        "dry_run": False,
                    }
                )
                conn.execute(
                    "INSERT INTO audit_log (event_type, run_hash, actor, ts, details_json) VALUES (?, ?, ?, ?, ?)",
                    (
                        "schema_version_backfill",
                        run_hash,
                        "governance_migration",
                        ts_seconds,
                        details,
                    ),
                )
            conn.commit()

    return BackfillSummary(
        total=len(runs),
        candidates=len(candidates),
        updated=len(candidates) if apply else 0,
        dry_run=not apply,
        schema_version=target,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Backfill manifest schema_version fields"
    )
    parser.add_argument(
        "--apply", action="store_true", help="Apply changes (default dry-run)"
    )
    parser.add_argument(
        "--schema-version",
        dest="schema_version",
        help="Override target schema version (defaults to contract version)",
    )
    args = parser.parse_args(argv)
    summary = run_backfill(apply=args.apply, schema_version=args.schema_version)
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(
        f"[{mode}] runs={summary.total} candidates={summary.candidates} target={summary.schema_version} updated={summary.updated}"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())

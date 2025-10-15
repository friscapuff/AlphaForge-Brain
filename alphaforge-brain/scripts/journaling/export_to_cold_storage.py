"""Pack journaling artifacts for cold storage and append retention evidence.

Phase 016 (T036) introduces a CLI helper that prepares enriched journaling
artifacts for cold storage while recording the export timestamp in the
retention audit log. The script intentionally reuses the existing cold storage
infrastructure so operators can offload bundles immediately when the
environment is configured.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import tarfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from domain.run.retention_policy import load_retention_config
from services.audit.governance_logger import append_audit_log
from services.journaling.artifact_paths import resolve_journaling_root

from infra.artifacts_root import resolve_artifact_root
from infra.cold_storage import offload


def export_to_cold_storage(
    run_id: str,
    *,
    journaling_root: Path | None = None,
    artifact_root: Path | None = None,
    retention_log: Path | None = None,
    upload: bool = True,
) -> dict[str, object]:
    """Package journaling artifacts for cold storage and log the export.

    Parameters
    ----------
    run_id:
        Identifier of the run whose journaling artifacts will be exported.
    journaling_root:
        Optional override for the enriched journaling artifact root. Defaults to
        the canonical ``zz_artifacts/journaling`` root.
    artifact_root:
        Optional override for the cold-storage staging directory. Defaults to the
        primary ``artifacts`` root resolved by :mod:`infra.artifacts_root`.
    retention_log:
        Optional override for the evidence log path. Defaults to the path defined
        in the retention policy configuration.
    upload:
        When ``True`` (default) the script invokes the cold storage offload helper.

    Returns
    -------
    dict[str, object]
        Metadata describing the export (timestamps, archive path, hash signature).
    """

    journal_base = resolve_journaling_root(journaling_root)
    run_path = journal_base / run_id
    if not run_path.exists():
        raise FileNotFoundError(
            f"journaling artifacts not found for run '{run_id}' at {run_path}"
        )

    files = sorted(_iter_files(run_path))
    if not files:
        raise RuntimeError(f"no journaling files present for run '{run_id}'")

    exported_at = datetime.now(timezone.utc)
    artifact_base = resolve_artifact_root(artifact_root)
    staging_dir = artifact_base / run_id / "journaling" / "exports"
    staging_dir.mkdir(parents=True, exist_ok=True)

    archive_name = f"journaling-{run_id}-{exported_at.strftime('%Y%m%dT%H%M%SZ')}"
    archive_path = staging_dir / f"{archive_name}.tar.gz"

    archive_bytes = _build_archive(run_path, files)
    archive_path.write_bytes(archive_bytes)

    if upload:
        offload(run_id, [archive_path])
        if not archive_path.exists():
            archive_path.write_bytes(archive_bytes)

    metadata = _build_metadata(
        run_id=run_id,
        run_path=run_path,
        files=files,
        archive_path=archive_path,
        exported_at=exported_at,
    )

    metadata_path = staging_dir / f"{archive_name}.manifest.json"
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8"
    )
    metadata["metadata_path"] = str(metadata_path)

    log_path = retention_log or load_retention_config().audit_log_path
    _append_retention_log(
        run_id=run_id,
        metadata=metadata,
        exported_at=exported_at,
        log_path=log_path,
    )

    cold_manifest = archive_path.parent.parent.parent / "cold_manifest.json"
    if cold_manifest.exists():
        metadata["cold_storage_manifest"] = str(cold_manifest)

    return metadata


def _iter_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if path.is_file():
            yield path


def _build_archive(run_path: Path, files: Sequence[Path]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(mode="w:gz", fileobj=buffer) as archive:
        for file_path in files:
            arcname = file_path.relative_to(run_path).as_posix()
            archive.add(file_path, arcname=arcname)
    return buffer.getvalue()


def _extract_signature(run_path: Path) -> str | None:
    trade_path = run_path / "completed_trades.json"
    if not trade_path.exists():
        return None
    try:
        trades = json.loads(trade_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if isinstance(trades, list):
        for record in trades:
            if isinstance(record, dict) and record.get("hash_signature"):
                return str(record["hash_signature"])
    return None


def _load_aggregate(run_path: Path) -> dict[str, object] | None:
    aggregate_path = run_path / "aggregates.json"
    if not aggregate_path.exists():
        return None
    try:
        payload = json.loads(aggregate_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict):
        return payload
    return None


def _build_metadata(
    *,
    run_id: str,
    run_path: Path,
    files: Sequence[Path],
    archive_path: Path,
    exported_at: datetime,
) -> dict[str, object]:
    signature = _extract_signature(run_path)
    aggregate = _load_aggregate(run_path)
    relative_files = [file.relative_to(run_path).as_posix() for file in files]

    metadata: dict[str, object] = {
        "event": "journaling.cold_storage.packaged",
        "run_id": run_id,
        "exported_at": exported_at.isoformat(),
        "archive_path": str(archive_path),
        "file_count": len(relative_files),
        "files": relative_files,
        "bytes": archive_path.stat().st_size,
        "source_root": str(run_path),
    }
    if signature:
        metadata["hash_signature"] = signature
    source_artifacts: list[str] | None = None
    if aggregate:
        metadata["aggregate_schema_version"] = aggregate.get("schema_version")
        metadata["aggregate_context_version"] = aggregate.get("context_version")
        metadata["aggregate_hash"] = aggregate.get("artifact_hash")
        if aggregate.get("source_artifacts"):
            source_artifacts = list(aggregate.get("source_artifacts") or [])
    if source_artifacts is None:
        source_artifacts = [
            entry for entry in relative_files if not entry.startswith("snapshots/")
        ]
    metadata["source_artifacts"] = source_artifacts
    return metadata


def _append_retention_log(
    *,
    run_id: str,
    metadata: Mapping[str, object],
    exported_at: datetime,
    log_path: Path,
) -> None:
    deadline = exported_at + timedelta(hours=24)
    payload = {
        "event": "journaling.cold_storage.exported",
        "run_id": run_id,
        "exported_at": exported_at.isoformat(),
        "deadline_at": deadline.isoformat(),
        "archive_path": metadata.get("archive_path"),
        "file_count": metadata.get("file_count"),
        "hash_signature": metadata.get("hash_signature"),
        "source_artifacts": metadata.get("source_artifacts", []),
    }
    append_audit_log(payload=payload, audit_path=log_path)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export journaling artifacts for cold storage"
    )
    parser.add_argument("run_id", help="Run identifier to export")
    parser.add_argument(
        "--journaling-root",
        type=Path,
        default=None,
        help="Override journaling artifact root (defaults to zz_artifacts/journaling)",
    )
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=None,
        help="Override artifact root used for cold storage staging (defaults to ./artifacts)",
    )
    parser.add_argument(
        "--retention-log",
        type=Path,
        default=None,
        help="Override retention evidence log path",
    )
    parser.add_argument(
        "--skip-upload",
        action="store_true",
        help="Skip invoking the cold storage offload helper",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    metadata = export_to_cold_storage(
        args.run_id,
        journaling_root=args.journaling_root,
        artifact_root=args.artifact_root,
        retention_log=args.retention_log,
        upload=not args.skip_upload,
    )
    json.dump(metadata, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())

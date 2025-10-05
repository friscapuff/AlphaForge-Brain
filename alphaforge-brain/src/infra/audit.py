"""Simple append-only JSON lines audit log for retention events.

Writes to artifacts_root / "audit.log". Each line is a compact JSON object:
{"ts":"ISO8601","event":"PIN","run_hash":"...","details":{...}}

Events: PIN, UNPIN, RETENTION_APPLY, DEMOTE, REHYDRATE

For now this is best-effort and synchronous; if write fails we swallow exceptions.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from infra.artifacts_root import resolve_artifact_root

AUDIT_FILENAME = "audit.log"
AUDIT_ROTATED_PREFIX = "audit.log."
INTEGRITY_SNAPSHOT = "audit_integrity.json"
DEFAULT_ROTATE_BYTES = 1_000_000  # ~1MB default

# In-memory rotation metrics (process lifetime). Optional exposure via metrics endpoint.
_ROTATION_COUNT = 0
_ROTATED_ORIGINAL_BYTES = 0
_ROTATED_COMPRESSED_BYTES = 0


def _rotation_threshold() -> int:
    try:
        env_val = os.getenv("AF_AUDIT_ROTATE_BYTES")
        if env_val:
            v = int(env_val)
            if v <= 0:  # ignore non-positive values
                return DEFAULT_ROTATE_BYTES
            # clamp to a safe upper bound (100MB) to avoid runaway logs
            return min(v, 100_000_000)
    except Exception:  # pragma: no cover - resilience
        return DEFAULT_ROTATE_BYTES
    return DEFAULT_ROTATE_BYTES


def _audit_path(base: Path | None = None) -> Path:
    root = resolve_artifact_root(base)
    root.mkdir(parents=True, exist_ok=True)
    return root / AUDIT_FILENAME


def _rotate_if_needed(path: Path) -> None:
    """Rotate audit log if size threshold exceeded.

    Rotation scheme: audit.log -> audit.log.<epoch_seconds>.gz (gzip compressed for space).
    Writes integrity snapshot capturing last record hash so consumers can anchor trust chain.
    """
    try:
        threshold = _rotation_threshold()
        if not path.exists():
            return
        size = path.stat().st_size
        if size < threshold:
            return
        # Capture last line hash for integrity snapshot
        last_hash: str | None = None
        try:
            *_, last = (ln for ln in path.read_text("utf-8").splitlines() if ln.strip())
            prev = json.loads(last)
            last_hash = prev.get("hash")
        except Exception:  # pragma: no cover - resilience
            last_hash = None
        ts_suffix = int(datetime.now(timezone.utc).timestamp())
        rotated = path.with_name(f"{AUDIT_ROTATED_PREFIX}{ts_suffix}.gz")
        global _ROTATION_COUNT, _ROTATED_ORIGINAL_BYTES, _ROTATED_COMPRESSED_BYTES
        try:
            raw = path.read_bytes()
            before = len(raw)
            buf = gzip.compress(raw)
            with open(rotated, "wb") as gz:
                gz.write(buf)
            after = len(buf)
            path.unlink(missing_ok=True)
            _ROTATION_COUNT += 1
            _ROTATED_ORIGINAL_BYTES += before
            _ROTATED_COMPRESSED_BYTES += after
        except Exception:
            return  # can't rotate, abort silently
        # Write integrity snapshot
        snap = {
            "rotated_at": datetime.now(timezone.utc).isoformat(),
            "last_hash": last_hash,
            "rotated_file": rotated.name,
            "compressed": True,
            "threshold_bytes": threshold,
        }
        try:
            snap_path = rotated.parent / INTEGRITY_SNAPSHOT
            snap_path.write_text(
                json.dumps(snap, separators=(",", ":"), sort_keys=True),
                encoding="utf-8",
            )
        except Exception:  # pragma: no cover
            pass
    except Exception:  # pragma: no cover
        pass


def write_event(event: str, run_hash: str | None = None, **details: Any) -> None:
    """Append an audit event with hash-chain integrity metadata.

    Adds prev_hash and hash fields so consumers can verify no tampering occurred.
    Hash covers all fields except the trailing 'hash' itself. prev_hash for first record is None.
    """
    rec: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
    }
    if run_hash is not None:
        rec["run_hash"] = run_hash
    if details:
        rec["details"] = details
    try:
        path = _audit_path(None)
        prev_hash: str | None = None
        if path.exists():
            try:
                # Read last non-empty line to extract prior hash
                *_, last = (
                    ln for ln in path.read_text("utf-8").splitlines() if ln.strip()
                )
                prev = json.loads(last)
                prev_hash = prev.get("hash")
            except Exception:  # pragma: no cover - resilience
                prev_hash = None
        if prev_hash:
            rec["prev_hash"] = prev_hash
        else:
            rec["prev_hash"] = None
        # Compute hash (excluding the future 'hash' key)
        serial = json.dumps(rec, separators=(",", ":"), sort_keys=True).encode()
        digest = hashlib.sha256(serial).hexdigest()
        rec["hash"] = digest
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, separators=(",", ":"), sort_keys=True))
            f.write("\n")
        # Attempt rotation post-write (size increases monotonically)
        _rotate_if_needed(path)
    except Exception:  # pragma: no cover
        pass


__all__ = ["write_event"]


def rotation_metrics() -> dict[str, int]:  # pragma: no cover - trivial getter
    return {
        "rotation_count": _ROTATION_COUNT,
        "rotated_original_bytes": _ROTATED_ORIGINAL_BYTES,
        "rotated_compressed_bytes": _ROTATED_COMPRESSED_BYTES,
    }


__all__.append("rotation_metrics")

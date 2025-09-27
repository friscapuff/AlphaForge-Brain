"""Cold storage offload / restore infrastructure.

Environment configuration (opt-in):

    AF_COLD_STORAGE_ENABLED=1            -> enable offload pipeline
    AF_COLD_STORAGE_PROVIDER=s3|gcs|local
    AF_COLD_STORAGE_BUCKET=<bucket name>  (required for s3/gcs)
    AF_COLD_STORAGE_PREFIX=<optional key prefix>

S3 requirements (optional dependency via poetry extra 'storage'):
    boto3 must be importable. Credentials resolved via standard AWS chain.

GCS requirements (future / placeholder):
    google-cloud-storage must be importable. (Not currently declared; left for future task)

Design:
    - Offload packs all target files for a run into a .tar.gz (stream) and uploads single object
        named: <prefix>/runs/<run_hash>/<ts>.tar.gz (or local mirror if provider=local)
    - A small JSON manifest (cold_manifest.json) written alongside run artifacts capturing
        object key, byte counts, timestamp, and list of original file names.
    - After successful upload original files are deleted (manifest & marker remain) so retention
        can free disk. (Eviction step already moves files to .evicted; we offload from there or main.)
    - Restore downloads the tar.gz, extracts any missing files back into the artifact directory
        (skips existing). Updates manifest with restore timestamp.

Resilience:
    - All functions are best-effort and swallow exceptions (logged via print fallback) so they do
        not disrupt retention pathways. Tests can monkeypatch provider classes for deterministic paths.
"""

from __future__ import annotations

import io
import json
import os
import tarfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Protocol, runtime_checkable

_MANIFEST_NAME = "cold_manifest.json"


def cold_storage_enabled() -> bool:
    return os.getenv("AF_COLD_STORAGE_ENABLED") == "1"


def _provider_name() -> str:
    return os.getenv("AF_COLD_STORAGE_PROVIDER", "local")


def _bucket() -> str | None:
    return os.getenv("AF_COLD_STORAGE_BUCKET")


def _prefix() -> str:
    return os.getenv("AF_COLD_STORAGE_PREFIX", "")


@runtime_checkable
class ColdStorageProvider(Protocol):  # pragma: no cover - structural
    def put_object(self, key: str, data: bytes) -> None: ...
    def get_object(self, key: str) -> bytes: ...


@dataclass
class LocalMirrorProvider:
    """Fallback provider: stores objects under artifacts_root/cold-mirror.

    Useful for tests without external dependencies.
    """

    root: Path

    def put_object(self, key: str, data: bytes) -> None:  # pragma: no cover - trivial
        dest = self.root / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)

    def get_object(self, key: str) -> bytes:  # pragma: no cover - trivial
        dest = self.root / key
        return dest.read_bytes()


def _resolve_artifacts_root() -> Path:
    from infra.artifacts_root import resolve_artifact_root

    return resolve_artifact_root(None)


def _provider() -> ColdStorageProvider | None:
    name = _provider_name().lower()
    base = _resolve_artifacts_root()
    if name == "local":
        return LocalMirrorProvider(base / "cold-mirror")
    if name == "s3":
        try:  # pragma: no cover - optional dependency
            import boto3

            s3 = boto3.client("s3")
        except Exception:  # pragma: no cover
            return None

        bucket = _bucket()
        if not bucket:
            return None

        class _S3Provider:
            def put_object(self, key: str, data: bytes) -> None:  # pragma: no cover
                s3.put_object(Bucket=bucket, Key=key, Body=data)

            def get_object(self, key: str) -> bytes:  # pragma: no cover
                r = s3.get_object(Bucket=bucket, Key=key)
                return r["Body"].read()

        return _S3Provider()
    if name == "gcs":  # Placeholder minimal implementation
        try:  # pragma: no cover - optional future dependency
            from google.cloud import storage
        except Exception:
            return None
        bucket_name = _bucket()
        if not bucket_name:
            return None
        client = storage.Client()
        bucket_obj = client.bucket(bucket_name)

        class _GCSProvider:
            def put_object(self, key: str, data: bytes) -> None:  # pragma: no cover
                blob = bucket_obj.blob(key)
                blob.upload_from_string(data)

            def get_object(self, key: str) -> bytes:  # pragma: no cover
                blob = bucket_obj.blob(key)
                return blob.download_as_bytes()

        return _GCSProvider()
    return None


def _manifest_path(run_hash: str) -> Path:
    base = _resolve_artifacts_root()
    return base / run_hash / _MANIFEST_NAME


def _run_dir(run_hash: str) -> Path:
    base = _resolve_artifacts_root()
    return base / run_hash


def offload(
    run_hash: str, files: Iterable[Path]
) -> None:  # pragma: no cover - network interactions
    if not cold_storage_enabled():
        return
    prov = _provider()
    if prov is None:
        return
    # Build tar.gz in memory
    file_list = list(files)
    if not file_list:
        return
    try:
        buf = io.BytesIO()
        with tarfile.open(mode="w:gz", fileobj=buf) as tf:
            for p in file_list:
                if not p.exists() or not p.is_file():
                    continue
                tf.add(p, arcname=p.name)
        payload = buf.getvalue()
        ts = int(time.time())
        key = f"{_prefix().rstrip('/')}/runs/{run_hash}/{ts}.tar.gz".lstrip("/")
        prov.put_object(key, payload)
        # Write manifest with metadata
        manifest = {
            "provider": _provider_name(),
            "key": key,
            "run_hash": run_hash,
            "created_at": ts,
            "files": [p.name for p in file_list],
            "bytes": len(payload),
            "count": len(file_list),
        }
        mp = _manifest_path(run_hash)
        try:
            mp.write_text(
                json.dumps(manifest, separators=(",", ":"), sort_keys=True),
                encoding="utf-8",
            )
        except Exception:
            pass
        # Delete original files after successful upload (conservative: skip manifest & .evicted marker)
        for p in file_list:
            if p.name in {"manifest.json", _MANIFEST_NAME, ".evicted"}:
                continue
            try:
                p.unlink(missing_ok=True)
            except Exception:
                pass
    except Exception:
        # Silent failure to avoid disrupting retention
        pass


def restore(run_hash: str) -> bool:  # pragma: no cover - network interactions
    if not cold_storage_enabled():
        return False
    prov = _provider()
    if prov is None:
        return False
    mp = _manifest_path(run_hash)
    if not mp.exists():
        return False
    try:
        manifest = json.loads(mp.read_text("utf-8"))
        key = manifest.get("key")
        if not key:
            return False
        data = prov.get_object(key)
        buf = io.BytesIO(data)
        restored_any = False
        target_dir = _run_dir(run_hash)
        target_dir.mkdir(parents=True, exist_ok=True)
        with tarfile.open(mode="r:gz", fileobj=buf) as tf:
            for m in tf.getmembers():
                out_path = target_dir / m.name
                if out_path.exists():
                    continue
                try:
                    tf.extract(m, path=target_dir)
                    restored_any = True
                except Exception:
                    pass
        # update manifest with restore event
        manifest["restored_at"] = int(time.time())
        try:
            mp.write_text(
                json.dumps(manifest, separators=(",", ":"), sort_keys=True),
                encoding="utf-8",
            )
        except Exception:
            pass
        return restored_any
    except Exception:
        return False


__all__ = [
    "cold_storage_enabled",
    "offload",
    "restore",
]

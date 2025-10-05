from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypedDict

"""Preset persistence service (T057).

Provides simple JSON-file backed persistence (single-user) plus in-memory cache.
Directory layout:
    presets/
        <preset_id>.json   # {"name":..., "config":..., "created_at":...}

Hash key: sha256 over canonical {"name":..., "config":...} truncated to 16 chars.

Future extension: optional SQLite table for indexing & metadata.
"""


class PresetRecord(TypedDict):
    name: str
    config: dict[str, Any]
    created_at: str


class PresetService:
    """File (directory or single JSON) backed preset persistence with in-memory cache.

    Thread-safety: a simple re-entrant lock protects cache + filesystem mutations.
    """

    def __init__(self, root: Path | None = None) -> None:
        env_path = os.getenv("ALPHAFORGE_PRESET_PATH") if root is None else None
        if root is None:
            if env_path:
                root = Path(env_path).parent
                self._single_file: Path | None = Path(env_path)
            else:
                root = Path("presets")
                self._single_file = None
        else:
            self._single_file = None
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, PresetRecord] = {}
        self._lock = threading.RLock()
        self._load_existing()

    def _load_existing(self) -> None:
        if getattr(self, "_single_file", None):
            sf = self._single_file
            if sf and sf.exists():
                try:
                    data_all = json.loads(sf.read_text("utf-8"))
                    if isinstance(data_all, dict):
                        for preset_id, rec in data_all.items():
                            if (
                                isinstance(rec, dict)
                                and "name" in rec
                                and "config" in rec
                            ):
                                created_at = (
                                    rec.get("created_at")
                                    or datetime.now(timezone.utc).isoformat()
                                )
                                self._cache[preset_id] = PresetRecord(
                                    name=rec["name"],
                                    config=rec["config"],
                                    created_at=created_at,
                                )
                except Exception:  # pragma: no cover - best effort
                    pass
            return
        for p in self.root.glob("*.json"):
            try:
                data = json.loads(p.read_text("utf-8"))
                preset_id = p.stem
                if isinstance(data, dict) and "name" in data and "config" in data:
                    created_at = (
                        data.get("created_at") or datetime.now(timezone.utc).isoformat()
                    )
                    self._cache[preset_id] = PresetRecord(
                        name=data["name"], config=data["config"], created_at=created_at
                    )
            except Exception:  # pragma: no cover - ignore corrupt files
                pass

    @staticmethod
    def _hash(name: str, config: dict[str, Any]) -> str:
        canonical = json.dumps(
            {"name": name, "config": config}, sort_keys=True, separators=(",", ":")
        ).encode()
        return hashlib.sha256(canonical).hexdigest()[:16]

    def create(self, name: str, config: dict[str, Any]) -> tuple[str, bool]:
        preset_id = self._hash(name, config)
        with self._lock:
            if preset_id in self._cache:
                return preset_id, False
            rec: PresetRecord = PresetRecord(
                name=name,
                config=config,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            self._cache[preset_id] = rec
            self._flush(new_ids=[preset_id])
            return preset_id, True

    def get(self, preset_id: str) -> PresetRecord | None:
        return self._cache.get(preset_id)

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            # Return sorted by created_at ascending
            return sorted(
                [{"preset_id": pid, **rec} for pid, rec in self._cache.items()],
                key=lambda r: r.get("created_at", "") or "",
            )

    def delete(self, preset_id: str) -> bool:
        with self._lock:
            if preset_id not in self._cache:
                return False
            del self._cache[preset_id]
            # Remove on-disk file eagerly for directory mode
            if not getattr(self, "_single_file", None):
                path = self.root / f"{preset_id}.json"
                try:
                    if path.exists():
                        path.unlink()
                except Exception:  # pragma: no cover
                    pass
            self._flush()  # rewrite aggregate / or single file
            return True

    def _flush(self, new_ids: Iterable[str] | None = None) -> None:
        if getattr(self, "_single_file", None):
            try:
                if self._single_file is not None:
                    self._single_file.write_text(
                        json.dumps(self._cache, sort_keys=True), encoding="utf-8"
                    )
            except Exception:  # pragma: no cover
                pass
            return
        if new_ids:
            for nid in new_ids:
                rec = self._cache.get(nid)
                if rec is None:
                    continue
                path = self.root / f"{nid}.json"
                try:
                    path.write_text(json.dumps(rec, sort_keys=True), encoding="utf-8")
                except Exception:  # pragma: no cover
                    pass
        else:
            for pid, rec in self._cache.items():
                path = self.root / f"{pid}.json"
                try:
                    path.write_text(json.dumps(rec, sort_keys=True), encoding="utf-8")
                except Exception:  # pragma: no cover
                    pass


class SQLitePresetService(PresetService):
    """SQLite-backed preset service.

    Chosen when ALPHAFORGE_PRESET_BACKEND=sqlite. Provides indexing & single-file DB.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        if db_path is None:
            db_path = Path(os.getenv("ALPHAFORGE_PRESET_DB", "presets.db"))
        self.db_path = db_path
        self._conn = sqlite3.connect(self.db_path)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS presets(
              preset_id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              config_json TEXT NOT NULL,
              created_at TEXT NOT NULL,
              UNIQUE(name, config_json)
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_presets_name ON presets(name)"
        )
        self._conn.commit()

    def create(self, name: str, config: dict[str, Any]) -> tuple[str, bool]:
        pid = self._hash(name, config)
        cfg_json = json.dumps(config, sort_keys=True, separators=(",", ":"))
        cur = self._conn.cursor()
        created = False
        try:
            cur.execute(
                "INSERT INTO presets(preset_id, name, config_json, created_at) VALUES(?,?,?,?)",
                (pid, name, cfg_json, datetime.now(timezone.utc).isoformat()),
            )
            created = True
            self._conn.commit()
        except sqlite3.IntegrityError:
            pass
        return pid, created

    def get(self, preset_id: str) -> PresetRecord | None:
        cur = self._conn.cursor()
        cur.execute(
            "SELECT name, config_json, created_at FROM presets WHERE preset_id=?",
            (preset_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        name, cfg_json, created_at = row
        return PresetRecord(
            name=name, config=json.loads(cfg_json), created_at=created_at
        )

    def list(self) -> list[dict[str, Any]]:
        cur = self._conn.cursor()
        cur.execute(
            "SELECT preset_id, name, config_json, created_at FROM presets ORDER BY created_at ASC"
        )
        rows = cur.fetchall()
        return [
            {
                "preset_id": pid,
                "name": name,
                "config": json.loads(cfg_json),
                "created_at": created_at,
            }
            for pid, name, cfg_json, created_at in rows
        ]

    def delete(self, preset_id: str) -> bool:
        cur = self._conn.cursor()
        cur.execute("DELETE FROM presets WHERE preset_id=?", (preset_id,))
        if cur.rowcount:
            self._conn.commit()
            return True
        return False

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:  # pragma: no cover
            pass

    # Allow context manager usage for temporary services
    def __enter__(
        self,
    ) -> SQLitePresetService:  # pragma: no cover - rarely used in prod path
        return self

    from types import TracebackType

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:  # pragma: no cover
        self.close()


def _make_service_from_env() -> PresetService:
    backend = os.getenv("ALPHAFORGE_PRESET_BACKEND", "file").lower()
    if backend == "sqlite":
        return SQLitePresetService()
    return PresetService()


# Singleton accessor (simple module-level cache for API layer)
_service: PresetService | None = None


def get_preset_service() -> PresetService:
    global _service
    env_backend = os.getenv("ALPHAFORGE_PRESET_BACKEND", "file").lower()
    env_path = os.getenv("ALPHAFORGE_PRESET_PATH")
    if _service is None:
        _service = _make_service_from_env()
        return _service
    # Recreate service if backend type changed (file<->sqlite) or single-file path changed
    backend_mismatch = (
        env_backend == "sqlite" and not isinstance(_service, SQLitePresetService)
    ) or (env_backend != "sqlite" and isinstance(_service, SQLitePresetService))
    path_mismatch = False
    if env_path and not isinstance(
        _service, SQLitePresetService
    ):  # only relevant for file backend
        existing_sf = getattr(_service, "_single_file", None)
        path_mismatch = bool(existing_sf) and str(existing_sf) != env_path
    if backend_mismatch or path_mismatch:
        _service = _make_service_from_env()
    return _service


__all__ = ["PresetService", "SQLitePresetService", "get_preset_service"]

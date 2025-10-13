from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from . import config as _config_mod
from .logging import get_logger

LOGGER = get_logger(__name__)


def _init_db(path: Path) -> None:
    first = not path.exists()
    conn = sqlite3.connect(path)
    try:
        if first:
            LOGGER.info("db_initializing", path=str(path))
        _apply_migrations(conn)
    finally:
        conn.close()


def _apply_migrations(conn: sqlite3.Connection) -> None:
    # Append-only migration runner. Enumerates packaged SQL files and applies missing ones in order.
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations (id TEXT PRIMARY KEY, applied_at INTEGER NOT NULL)"
    )
    existing = {row[0] for row in conn.execute("SELECT id FROM schema_migrations")}
    # Discover migrations in infra.migrations package
    try:
        from importlib import resources as _resources

        pkg = __package__ + ".migrations"
        sql_files = [
            e.name for e in _resources.files(pkg).iterdir() if e.name.endswith(".sql")
        ]
        sql_files.sort()  # ensure 001_, 002_, ... order
    except Exception as e:
        LOGGER.error("migration_enumeration_failed", error=str(e))
        sql_files = ["001_init.sql"]  # fallback
    for filename in sql_files:
        mig_id = filename.rsplit(".", 1)[0]  # e.g., 001_init
        if mig_id in existing:
            continue
        try:
            from .migrations import load_sql

            sql = load_sql(filename)
        except Exception as e:  # pragma: no cover - defensive
            LOGGER.warning("migration_missing", id=mig_id, name=filename, error=str(e))
            continue
        LOGGER.info("migration_applying", id=mig_id)
        conn.executescript(sql)
        conn.execute(
            "INSERT INTO schema_migrations (id, applied_at) VALUES (?, strftime('%s','now'))",
            (mig_id,),
        )
    conn.commit()
    try:
        from .alembic import apply_python_migrations  # lazy import to avoid circulars

        apply_python_migrations(conn)
    except ModuleNotFoundError:
        LOGGER.debug("migration.python.skip", reason="alembic_package_missing")
    except Exception as exc:  # pragma: no cover - defensive logging
        LOGGER.error("migration.python.failed", error=str(exc))
        raise

    _ensure_legacy_columns(conn)


def _ensure_legacy_columns(conn: sqlite3.Connection) -> None:
    """Ensure legacy governance columns exist for backward compatibility."""

    try:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='runs'"
        )
        if cur.fetchone() is None:
            return
        existing = {row[1] for row in conn.execute("PRAGMA table_info(runs)")}
        required: dict[str, str] = {
            "updated_at": "INTEGER",
            "config_json": "TEXT",
            "data_hash": "TEXT",
            "seed_root": "INTEGER",
            "db_version": "INTEGER",
            "bootstrap_seed": "INTEGER",
            "walk_forward_spec_json": "TEXT",
        }
        added = False
        for column, column_type in required.items():
            if column not in existing:
                conn.execute(f"ALTER TABLE runs ADD COLUMN {column} {column_type}")
                added = True
        if added:
            conn.commit()
    except Exception as exc:  # pragma: no cover - defensive
        LOGGER.warning("runs.legacy_columns.ensure_failed", error=str(exc))


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    path = _resolve_sqlite_path()
    _init_db(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        if conn.in_transaction:
            conn.commit()
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise
    finally:
        conn.close()


def _resolve_sqlite_path() -> Path:
    env_override = os.getenv("APP_SQLITE_PATH")
    if env_override:
        cached = _config_mod.get_settings()
        override_path = Path(env_override)
        if override_path != cached.sqlite_path:
            cache_clear = getattr(_config_mod.get_settings, "cache_clear", None)
            if callable(cache_clear):
                cache_clear()
            return _config_mod.get_settings().sqlite_path
        return override_path
    return _config_mod.get_settings().sqlite_path


__all__ = ["get_connection"]

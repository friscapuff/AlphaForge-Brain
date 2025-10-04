from __future__ import annotations

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


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    settings = _config_mod.get_settings()
    path = settings.sqlite_path
    _init_db(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


__all__ = ["get_connection"]

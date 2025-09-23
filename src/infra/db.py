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
    # Simple migration runner (append-only). For now load 001_init.sql if not applied.
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations (id TEXT PRIMARY KEY, applied_at INTEGER NOT NULL)"
    )
    existing = {row[0] for row in conn.execute("SELECT id FROM schema_migrations")}
    migrations = [("001_init", Path("infra/migrations/001_init.sql"))]
    for mig_id, mig_path in migrations:
        if mig_id in existing:
            continue
        if not mig_path.exists():
            LOGGER.warning("migration_missing", id=mig_id, path=str(mig_path))
            continue
        sql = mig_path.read_text(encoding="utf-8")
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

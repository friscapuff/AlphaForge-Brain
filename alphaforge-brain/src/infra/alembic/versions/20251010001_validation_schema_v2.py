from __future__ import annotations

import json
import sqlite3
from typing import Any

revision = "20251010001"
description = "Validation schema v2 columns and metadata"


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    )
    return cur.fetchone() is not None


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())


def _ensure_json1(conn: sqlite3.Connection) -> None:
    try:
        conn.execute("SELECT json('null')")
    except sqlite3.OperationalError as exc:  # pragma: no cover - defensive guard
        raise RuntimeError(
            "SQLite JSON1 extension is required for validation metadata"
        ) from exc


def _create_validation_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS validation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_hash TEXT NOT NULL,
            method TEXT,
            params_json TEXT,
            results_json TEXT,
            ci_width REAL,
            p_value REAL,
            content_hash TEXT,
            validation_type TEXT,
            segment_id TEXT,
            effect_size REAL,
            permutation_count INTEGER,
            dsr REAL,
            psr REAL,
            bias_flag INTEGER,
            leakage_score REAL,
            realism_status TEXT,
            metadata_json TEXT,
            FOREIGN KEY(run_hash) REFERENCES runs(run_hash)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_validation_run_hash ON validation(run_hash)"
    )


def _migrate_existing_validation(conn: sqlite3.Connection) -> None:
    if not _table_exists(conn, "validation"):
        _create_validation_table(conn)
        return

    needs_migration = not _column_exists(conn, "validation", "validation_type")
    if not needs_migration:
        if not _column_exists(conn, "validation", "metadata_json"):
            conn.execute("ALTER TABLE validation ADD COLUMN metadata_json TEXT")
        if not _column_exists(conn, "validation", "content_hash"):
            conn.execute("ALTER TABLE validation ADD COLUMN content_hash TEXT")
        if not _column_exists(conn, "validation", "method"):
            conn.execute("ALTER TABLE validation ADD COLUMN method TEXT")
        if not _column_exists(conn, "validation", "params_json"):
            conn.execute("ALTER TABLE validation ADD COLUMN params_json TEXT")
        if not _column_exists(conn, "validation", "results_json"):
            conn.execute("ALTER TABLE validation ADD COLUMN results_json TEXT")
        if not _column_exists(conn, "validation", "ci_width"):
            conn.execute("ALTER TABLE validation ADD COLUMN ci_width REAL")
        if not _column_exists(conn, "validation", "p_value"):
            conn.execute("ALTER TABLE validation ADD COLUMN p_value REAL")
        if not _column_exists(conn, "validation", "effect_size"):
            conn.execute("ALTER TABLE validation ADD COLUMN effect_size REAL")
        if not _column_exists(conn, "validation", "permutation_count"):
            conn.execute("ALTER TABLE validation ADD COLUMN permutation_count INTEGER")
        if not _column_exists(conn, "validation", "dsr"):
            conn.execute("ALTER TABLE validation ADD COLUMN dsr REAL")
        if not _column_exists(conn, "validation", "psr"):
            conn.execute("ALTER TABLE validation ADD COLUMN psr REAL")
        if not _column_exists(conn, "validation", "bias_flag"):
            conn.execute("ALTER TABLE validation ADD COLUMN bias_flag INTEGER")
        if not _column_exists(conn, "validation", "leakage_score"):
            conn.execute("ALTER TABLE validation ADD COLUMN leakage_score REAL")
        if not _column_exists(conn, "validation", "realism_status"):
            conn.execute("ALTER TABLE validation ADD COLUMN realism_status TEXT")
        if not _column_exists(conn, "validation", "segment_id"):
            conn.execute("ALTER TABLE validation ADD COLUMN segment_id TEXT")
        if not _column_exists(conn, "validation", "validation_type"):
            conn.execute("ALTER TABLE validation ADD COLUMN validation_type TEXT")
        return

    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute(
        """
        CREATE TABLE validation_backup AS SELECT * FROM validation
        """
    )
    conn.execute("DROP TABLE validation")
    _create_validation_table(conn)
    if _column_exists(conn, "validation_backup", "payload_json"):
        rows = conn.execute(
            "SELECT run_hash, payload_json, permutation_pvalue FROM validation_backup"
        ).fetchall()
        for run_hash, payload_json, permutation_pvalue in rows:
            metadata: dict[str, Any]
            try:
                metadata = json.loads(payload_json) if payload_json else {}
            except Exception:
                metadata = {"legacy_payload": payload_json}
            conn.execute(
                """
                INSERT INTO validation (
                    run_hash, validation_type, segment_id, p_value, metadata_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    run_hash,
                    "legacy",
                    "legacy",
                    (
                        float(permutation_pvalue)
                        if permutation_pvalue is not None
                        else None
                    ),
                    json.dumps(metadata, sort_keys=True),
                ),
            )
    conn.execute("DROP TABLE validation_backup")
    conn.execute("PRAGMA foreign_keys=ON")


def _ensure_runs_column(conn: sqlite3.Connection) -> None:
    if not _table_exists(conn, "runs"):
        return
    if not _column_exists(conn, "runs", "validation_schema_version"):
        conn.execute(
            "ALTER TABLE runs ADD COLUMN validation_schema_version INTEGER NOT NULL DEFAULT 1"
        )


def upgrade(conn: sqlite3.Connection) -> None:
    _ensure_json1(conn)
    _migrate_existing_validation(conn)
    _ensure_runs_column(conn)

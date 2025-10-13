from __future__ import annotations

import json
import sqlite3

revision = "20251011001"
description = "Trust gate persistence tables and manifest columns"


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
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
            "SQLite JSON1 extension is required for trust gate tables"
        ) from exc


def _create_trust_gate_suites(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS trust_gate_suites (
            suite_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            config_hash TEXT NOT NULL,
            enabled_gates TEXT NOT NULL,
            tolerance_profile TEXT,
            runtime_ms INTEGER,
            executed_at TEXT,
            status TEXT,
            suite_version INTEGER NOT NULL DEFAULT 1,
            report_path TEXT,
            signature_path TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_trust_gate_suites_run_id
            ON trust_gate_suites(run_id)
        """
    )


def _create_trust_gate_results(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS trust_gate_results (
            result_id TEXT PRIMARY KEY,
            suite_id TEXT NOT NULL,
            gate_type TEXT NOT NULL,
            status TEXT NOT NULL,
            metrics_json TEXT,
            tolerance_json TEXT,
            artifact_path TEXT,
            correlation_id TEXT,
            waiver_ref TEXT,
            duration_ms INTEGER,
            diagnostics_json TEXT,
            FOREIGN KEY(suite_id) REFERENCES trust_gate_suites(suite_id)
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_trust_gate_results_suite
            ON trust_gate_results(suite_id)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_trust_gate_results_gate
            ON trust_gate_results(gate_type)
        """
    )


def _ensure_runs_manifest_column(conn: sqlite3.Connection) -> None:
    if not _table_exists(conn, "runs"):
        return
    if not _column_exists(conn, "runs", "trust_gate_manifest"):
        conn.execute("ALTER TABLE runs ADD COLUMN trust_gate_manifest TEXT")
    required_columns = {
        "updated_at": "INTEGER",
        "config_json": "TEXT",
        "data_hash": "TEXT",
        "seed_root": "INTEGER",
        "db_version": "INTEGER",
        "bootstrap_seed": "INTEGER",
    }
    for column, column_type in required_columns.items():
        if not _column_exists(conn, "runs", column):
            conn.execute(f"ALTER TABLE runs ADD COLUMN {column} {column_type}")


def _ensure_baselines_columns(conn: sqlite3.Connection) -> None:
    if not _table_exists(conn, "baselines"):
        return
    if not _column_exists(conn, "baselines", "baseline_type"):
        conn.execute("ALTER TABLE baselines ADD COLUMN baseline_type TEXT")
    if not _column_exists(conn, "baselines", "trust_gate_version"):
        conn.execute("ALTER TABLE baselines ADD COLUMN trust_gate_version INTEGER")
    if not _column_exists(conn, "baselines", "signature"):
        conn.execute("ALTER TABLE baselines ADD COLUMN signature TEXT")


def _backfill_enabled_gates(conn: sqlite3.Connection) -> None:
    # For idempotency, ensure enabled_gates stored as canonical JSON array when possible
    if not _table_exists(conn, "trust_gate_suites"):
        return
    cur = conn.execute(
        "SELECT suite_id, enabled_gates FROM trust_gate_suites WHERE enabled_gates IS NOT NULL"
    )
    updates: list[tuple[str, str]] = []
    for suite_id, gates in cur.fetchall():
        if isinstance(gates, str):
            try:
                parsed = json.loads(gates)
            except Exception:  # pragma: no cover - tolerate legacy data
                parsed = gates.split(",") if gates else []
        else:
            parsed = []
        if isinstance(parsed, list):
            canonical = json.dumps(
                sorted({str(g).strip() for g in parsed if g}), sort_keys=True
            )
        else:
            canonical = json.dumps([])
        updates.append((canonical, suite_id))
    for canonical, suite_id in updates:
        conn.execute(
            "UPDATE trust_gate_suites SET enabled_gates=? WHERE suite_id=?",
            (canonical, suite_id),
        )


def upgrade(conn: sqlite3.Connection) -> None:
    _ensure_json1(conn)
    _create_trust_gate_suites(conn)
    _create_trust_gate_results(conn)
    _ensure_runs_manifest_column(conn)
    _ensure_baselines_columns(conn)
    _backfill_enabled_gates(conn)

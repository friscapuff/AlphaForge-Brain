"""Migration validation for schema version backfill (US2/T019)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from infra.db import get_connection
from scripts.migrations.backfill_schema_version import run_backfill


@pytest.fixture()
def temp_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    db_path = tmp_path / "studio.db"
    monkeypatch.setenv("APP_SQLITE_PATH", str(db_path))
    # trigger migrations to create schema
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO runs (run_hash, created_at, updated_at, status, config_json, manifest_json, data_hash, seed_root, db_version, bootstrap_seed) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "R1",
                0,
                0,
                "SUCCEEDED",
                json.dumps({"schema_version": "0.9.0"}),
                json.dumps({"files": []}),
                "hash",
                0,
                1,
                0,
            ),
        )
    return db_path


def _load_manifest(run_hash: str) -> dict[str, object]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT manifest_json FROM runs WHERE run_hash=?",
            (run_hash,),
        ).fetchone()
    assert row is not None
    return json.loads(row[0])


def _audit_events() -> list[dict[str, object]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT event_type, details_json FROM audit_log").fetchall()
    events = []
    for event_type, details in rows:
        parsed = json.loads(details) if details else {}
        parsed["event_type"] = event_type
        events.append(parsed)
    return events


def test_backfill_applies_schema_version(
    monkeypatch: pytest.MonkeyPatch, temp_db: Path
) -> None:
    summary = run_backfill(apply=True, schema_version="1.0.0")

    assert summary.updated == 1
    manifest = _load_manifest("R1")
    assert manifest["schema_version"] == "1.0.0"
    events = _audit_events()
    assert len(events) == 1
    assert events[0]["event_type"] == "schema_version_backfill"
    assert events[0]["run_hash"] == "R1"


def test_backfill_is_idempotent(monkeypatch: pytest.MonkeyPatch, temp_db: Path) -> None:
    run_backfill(apply=True, schema_version="1.0.1")
    first_events = _audit_events()

    summary = run_backfill(apply=True, schema_version="1.0.1")

    assert summary.updated == 0
    manifest = _load_manifest("R1")
    assert manifest["schema_version"] == "1.0.1"
    events = _audit_events()
    assert len(events) == len(first_events)

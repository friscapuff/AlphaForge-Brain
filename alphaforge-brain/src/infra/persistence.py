from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .db import get_connection
from .logging import get_logger
from .utils.hash import canonical_json, hash_canonical, sha256_hex

try:  # lightweight optional import for parquet shape
    import pyarrow.parquet as _pq  # type: ignore
except Exception:  # pragma: no cover - tests guard presence
    _pq = None  # type: ignore

LOGGER = get_logger(__name__)


# --- Write helpers (FR-100..105) ---


def init_run(
    *,
    run_hash: str,
    created_at_ms: int,
    status: str,
    config_json: dict[str, Any],
    manifest_json: dict[str, Any],
    data_hash: str,
    seed_root: int,
    db_version: int,
    bootstrap_seed: int,
    walk_forward_spec: dict[str, Any] | None = None,
) -> None:
    updated_at_ms = created_at_ms
    with get_connection() as conn:
        # Canonicalize JSON strings for deterministic storage and hashing
        cfg_text = canonical_json(config_json)
        man_text = canonical_json(manifest_json)
        cfg_hash = sha256_hex(cfg_text.encode("utf-8"))
        man_hash = sha256_hex(man_text.encode("utf-8"))
        conn.execute(
            """
            INSERT OR REPLACE INTO runs (
                run_hash, created_at, updated_at, status, config_json, manifest_json,
                data_hash, seed_root, db_version, bootstrap_seed, walk_forward_spec_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_hash,
                created_at_ms,
                updated_at_ms,
                status,
                cfg_text,
                man_text,
                data_hash,
                int(seed_root),
                int(db_version),
                int(bootstrap_seed),
                (
                    None
                    if walk_forward_spec is None
                    else json.dumps(
                        walk_forward_spec, sort_keys=True, separators=(",", ":")
                    )
                ),
            ),
        )
        # Persist content hashes into metrics for provenance (FR-140)
        conn.execute(
            "INSERT INTO metrics (run_hash, key, value, value_type, phase) VALUES (?, ?, ?, ?, ?)",
            (run_hash, "config_json_hash", cfg_hash, "sha256", "init"),
        )
        conn.execute(
            "INSERT INTO metrics (run_hash, key, value, value_type, phase) VALUES (?, ?, ?, ?, ?)",
            (run_hash, "manifest_json_hash", man_hash, "sha256", "init"),
        )
        conn.commit()


def update_run_status(*, run_hash: str, status: str, updated_at_ms: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE runs SET status=?, updated_at=? WHERE run_hash=?",
            (status, updated_at_ms, run_hash),
        )
        conn.commit()


def bulk_insert_trades(
    *,
    run_hash: str,
    rows: Iterable[
        tuple[
            int,
            str,
            float,
            float | None,
            float | None,
            float | None,
            float | None,
            float | None,
            float | None,
        ]
    ],
) -> None:
    with get_connection() as conn:
        conn.executemany(
            """
            INSERT INTO trades (
              run_hash, ts, side, qty, entry_price, exit_price, cost_bps, borrow_cost, pnl, position_after
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ((run_hash, *row) for row in rows),
        )
        conn.commit()


def bulk_insert_equity(
    *,
    run_hash: str,
    rows: Iterable[
        tuple[int, float | None, float | None, float | None, float | None, float | None]
    ],
) -> None:
    with get_connection() as conn:
        conn.executemany(
            """
            INSERT INTO equity (
              run_hash, ts, equity, drawdown, realized_pnl, unrealized_pnl, cost_drag
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ((run_hash, *row) for row in rows),
        )
        conn.commit()


def insert_metric(
    *, run_hash: str, key: str, value: str, value_type: str, phase: str | None
) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO metrics (run_hash, key, value, value_type, phase) VALUES (?, ?, ?, ?, ?)",
            (run_hash, key, value, value_type, phase),
        )
        conn.commit()


def finalize_run(
    *,
    run_hash: str,
    trades_rows: Iterable[
        tuple[
            int,
            str,
            float,
            float | None,
            float | None,
            float | None,
            float | None,
            float | None,
            float | None,
        ]
    ],
    equity_rows: Iterable[
        tuple[int, float | None, float | None, float | None, float | None, float | None]
    ],
    record_counts_phase: str = "finalize",
) -> tuple[int, int]:
    """Insert trades and equity in a single transaction and record row counts as metrics.

    Returns (n_trades, n_equity).
    """
    # Materialize counts while iterating once
    trades_list = list(trades_rows)
    equity_list = list(equity_rows)
    with get_connection() as conn:
        try:
            conn.execute("BEGIN")
            conn.executemany(
                """
                INSERT INTO trades (
                  run_hash, ts, side, qty, entry_price, exit_price, cost_bps, borrow_cost, pnl, position_after
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ((run_hash, *row) for row in trades_list),
            )
            conn.executemany(
                """
                INSERT INTO equity (
                  run_hash, ts, equity, drawdown, realized_pnl, unrealized_pnl, cost_drag
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ((run_hash, *row) for row in equity_list),
            )
            # Record row counts as metrics
            conn.execute(
                "INSERT INTO metrics (run_hash, key, value, value_type, phase) VALUES (?, ?, ?, ?, ?)",
                (
                    run_hash,
                    "rows_trades",
                    str(len(trades_list)),
                    "int",
                    record_counts_phase,
                ),
            )
            conn.execute(
                "INSERT INTO metrics (run_hash, key, value, value_type, phase) VALUES (?, ?, ?, ?, ?)",
                (
                    run_hash,
                    "rows_equity",
                    str(len(equity_list)),
                    "int",
                    record_counts_phase,
                ),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return len(trades_list), len(equity_list)


def insert_validation(
    *,
    run_hash: str,
    payload_json: dict[str, Any],
    permutation_pvalue: float | None,
    method: str | None,
    sharpe_ci: tuple[float | None, float | None] | None,
    cagr_ci: tuple[float | None, float | None] | None,
    block_length: int | None,
    jitter: int | None,
    fallback: bool | None,
) -> None:
    l_s, u_s = (None, None) if sharpe_ci is None else sharpe_ci
    l_c, u_c = (None, None) if cagr_ci is None else cagr_ci
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO validation (
                run_hash, payload_json, permutation_pvalue, bootstrap_sharpe_low, bootstrap_sharpe_high,
                bootstrap_cagr_low, bootstrap_cagr_high, bootstrap_method, bootstrap_block_length,
                bootstrap_jitter, bootstrap_fallback
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_hash,
                json.dumps(payload_json, sort_keys=True, separators=(",", ":")),
                permutation_pvalue,
                l_s,
                u_s,
                l_c,
                u_c,
                method,
                block_length,
                jitter,
                1 if fallback else 0 if fallback is not None else None,
            ),
        )
        conn.commit()


# --- Read helpers (FR-104) ---


def get_run(conn: sqlite3.Connection, run_hash: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM runs WHERE run_hash=?", (run_hash,)).fetchone()
    return dict(row) if row else None


def get_metrics(conn: sqlite3.Connection, run_hash: str) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT key, value, value_type, phase FROM metrics WHERE run_hash=?",
        (run_hash,),
    )
    return [dict(r) for r in cur.fetchall()]


# --- Typed reads (FR-104) ---


@dataclass(frozen=True)
class RunRow:
    run_hash: str
    created_at: int
    updated_at: int
    status: str
    config: dict[str, Any]
    manifest: dict[str, Any]
    data_hash: str
    seed_root: int
    db_version: int
    bootstrap_seed: int
    walk_forward_spec: dict[str, Any] | None


def get_run_typed(conn: sqlite3.Connection, run_hash: str) -> RunRow | None:
    row = conn.execute("SELECT * FROM runs WHERE run_hash=?", (run_hash,)).fetchone()
    if not row:
        return None
    wf = row["walk_forward_spec_json"]
    return RunRow(
        run_hash=row["run_hash"],
        created_at=int(row["created_at"]),
        updated_at=int(row["updated_at"]),
        status=row["status"],
        config=json.loads(row["config_json"]),
        manifest=json.loads(row["manifest_json"]),
        data_hash=row["data_hash"],
        seed_root=int(row["seed_root"]),
        db_version=int(row["db_version"]),
        bootstrap_seed=int(row["bootstrap_seed"]),
        walk_forward_spec=None if wf is None else json.loads(wf),
    )


# --- Feature cache metadata (FR-100, FR-103) ---


def upsert_feature_cache_meta(
    *,
    meta_hash: str,
    spec_json: dict[str, Any],
    built_at_ms: int,
    rows: int,
    columns: int,
    digest: str,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO features_cache (meta_hash, spec_json, built_at, rows, columns, digest)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(meta_hash) DO UPDATE SET
                spec_json=excluded.spec_json,
                built_at=excluded.built_at,
                rows=excluded.rows,
                columns=excluded.columns,
                digest=excluded.digest
            """,
            (
                meta_hash,
                json.dumps(spec_json, sort_keys=True, separators=(",", ":")),
                built_at_ms,
                rows,
                columns,
                digest,
            ),
        )
        conn.commit()


# --- Manifest validation hook (FR-141) ---


def validate_manifest_object(manifest: dict[str, Any], schema_path: Path) -> None:
    """Validate manifest object against JSON Schema.

    This is a light stub; actual schema validation wiring can use `jsonschema` or `fastjsonschema`.
    We avoid adding a new runtime dependency here; the CI/test can import a validator.
    """
    try:
        # Optional dependency pattern: import only if available.
        import jsonschema  # type: ignore[import-not-found]

        with schema_path.open("r", encoding="utf-8") as f:
            schema = json.load(f)
        jsonschema.validate(instance=manifest, schema=schema)  # type: ignore[attr-defined]
    except ModuleNotFoundError:
        LOGGER.info("manifest_validation_skipped", reason="jsonschema not installed")


__all__ = [
    "init_run",
    "update_run_status",
    "bulk_insert_trades",
    "bulk_insert_equity",
    "finalize_run",
    "insert_metric",
    "insert_validation",
    "get_run",
    "get_metrics",
    "get_run_typed",
    "RunRow",
    "validate_manifest_object",
    "upsert_feature_cache_meta",
    "record_feature_cache_artifact",
    "record_causality_stats",
    "record_phase_timing",
    "record_trace_span",
    "record_run_error",
    "record_phase_marker",
]


def _file_sha256(path: Path, chunk_size: int = 1 << 20) -> str:
    h = __import__("hashlib").sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def record_feature_cache_artifact(
    *,
    run_hash: str,
    parquet_path: Path,
    spec_json: dict[str, Any],
    built_at_ms: int | None = None,
) -> dict[str, Any]:
    """Persist features_cache metadata and wire into run.manifest_json.

    Returns the entry appended to manifest.features_cache.
    """
    if not parquet_path.exists():
        raise FileNotFoundError(str(parquet_path))

    meta_hash = hash_canonical(spec_json)
    digest = _file_sha256(parquet_path)

    # Obtain rows/columns cheaply without full pandas load when possible
    rows: int
    cols: int
    if _pq is not None:
        table = _pq.read_table(parquet_path)
        rows = int(table.num_rows)
        cols = int(table.num_columns)
    else:  # pragma: no cover
        import pandas as _pd

        df = _pd.read_parquet(parquet_path)
        rows = int(df.shape[0])
        cols = int(df.shape[1])

    upsert_feature_cache_meta(
        meta_hash=meta_hash,
        spec_json=spec_json,
        built_at_ms=0 if built_at_ms is None else built_at_ms,
        rows=rows,
        columns=cols,
        digest=digest,
    )

    # Update manifest_json in runs row
    with get_connection() as conn:
        row = conn.execute(
            "SELECT manifest_json FROM runs WHERE run_hash=?", (run_hash,)
        ).fetchone()
        if not row:
            raise KeyError(f"run not found: {run_hash}")
        manifest = json.loads(row[0])
        feats = manifest.get("features_cache")
        if not isinstance(feats, list):
            feats = []
        entry = {
            "meta_hash": meta_hash,
            "digest": digest,
            "rows": rows,
            "columns": cols,
            "path": str(parquet_path),
        }
        # de-dup by meta_hash; replace existing
        feats = [
            e
            for e in feats
            if not (isinstance(e, dict) and e.get("meta_hash") == meta_hash)
        ]
        feats.append(entry)
        manifest["features_cache"] = feats
        conn.execute(
            "UPDATE runs SET manifest_json=?, updated_at=strftime('%s','now')*1000 WHERE run_hash=?",
            (json.dumps(manifest, sort_keys=True, separators=(",", ":")), run_hash),
        )
        conn.commit()
    return entry


def record_causality_stats(
    *,
    run_hash: str,
    mode: str,
    violations: int,
    phase: str = "execution",
) -> None:
    """Record causality guard stats into metrics and persist into manifest_json."""
    with get_connection() as conn:
        # Metrics entries
        conn.execute(
            "INSERT INTO metrics (run_hash, key, value, value_type, phase) VALUES (?, ?, ?, ?, ?)",
            (run_hash, "causality_mode", mode, "str", phase),
        )
        conn.execute(
            "INSERT INTO metrics (run_hash, key, value, value_type, phase) VALUES (?, ?, ?, ?, ?)",
            (run_hash, "future_access_violations", str(int(violations)), "int", phase),
        )
        # Manifest update
        row = conn.execute(
            "SELECT manifest_json FROM runs WHERE run_hash=?", (run_hash,)
        ).fetchone()
        if row:
            manifest = json.loads(row[0])
            cg = manifest.get("causality_guard")
            if not isinstance(cg, dict):
                cg = {}
            cg["mode"] = mode
            cg["violations"] = int(violations)
            manifest["causality_guard"] = cg
            conn.execute(
                "UPDATE runs SET manifest_json=?, updated_at=strftime('%s','now')*1000 WHERE run_hash=?",
                (json.dumps(manifest, sort_keys=True, separators=(",", ":")), run_hash),
            )
        conn.commit()


# --- Observability & Phase instrumentation (FR-154, FR-155, FR-157) ---


def record_phase_timing(
    *,
    run_hash: str,
    phase: str,
    started_at_ms: int,
    ended_at_ms: int,
    rows_processed: int | None = None,
    extra_json: dict[str, Any] | None = None,
) -> None:
    duration_ms = max(0, int(ended_at_ms) - int(started_at_ms))
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO phase_metrics (run_hash, phase, started_at, ended_at, duration_ms, rows_processed, extra_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_hash,
                phase,
                int(started_at_ms),
                int(ended_at_ms),
                duration_ms,
                rows_processed,
                (
                    None
                    if extra_json is None
                    else json.dumps(extra_json, sort_keys=True, separators=(",", ":"))
                ),
            ),
        )
        conn.commit()


def record_trace_span(
    *,
    run_hash: str,
    name: str,
    started_at_ms: int,
    ended_at_ms: int,
    correlation_id: str | None = None,
    attributes: dict[str, Any] | None = None,
) -> None:
    """Persist a lightweight trace span as a phase_metrics row (phase=name)."""
    extra: dict[str, Any] = {}
    if correlation_id is not None:
        extra["correlation_id"] = correlation_id
    if attributes:
        extra["attributes"] = attributes
    record_phase_timing(
        run_hash=run_hash,
        phase=name,
        started_at_ms=started_at_ms,
        ended_at_ms=ended_at_ms,
        rows_processed=None,
        extra_json=extra or None,
    )


def record_run_error(
    *,
    run_hash: str,
    ts_ms: int,
    phase: str | None,
    error_code: str,
    message: str,
    stack_hash: str,
) -> None:
    """Persist an error record to run_errors (FR-156)."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO run_errors (run_hash, ts, phase, error_code, message, stack_hash)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (run_hash, int(ts_ms), phase, error_code, message, stack_hash),
        )
        conn.commit()


def record_phase_marker(*, run_hash: str, phase: str, ts_ms: int) -> None:
    """Record a phase completion marker in both phase_metrics (duration 0) and manifest_json."""
    # Phase metrics row (duration 0)
    record_phase_timing(
        run_hash=run_hash,
        phase=phase,
        started_at_ms=int(ts_ms),
        ended_at_ms=int(ts_ms),
        rows_processed=None,
        extra_json={"marker": "completed"},
    )
    # Manifest update marker map
    with get_connection() as conn:
        row = conn.execute(
            "SELECT manifest_json FROM runs WHERE run_hash=?", (run_hash,)
        ).fetchone()
        if row:
            manifest = json.loads(row[0])
            markers = manifest.get("phase_markers")
            if not isinstance(markers, dict):
                markers = {}
            markers[str(phase)] = int(ts_ms)
            manifest["phase_markers"] = markers
            conn.execute(
                "UPDATE runs SET manifest_json=?, updated_at=strftime('%s','now')*1000 WHERE run_hash=?",
                (json.dumps(manifest, sort_keys=True, separators=(",", ":")), run_hash),
            )
            conn.commit()

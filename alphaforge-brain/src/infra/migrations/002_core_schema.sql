-- Core schema expansion per Spec 004 (FR-100..105, 140..142)
-- Idempotent guards via IF NOT EXISTS for SQLite simplicity.

CREATE TABLE IF NOT EXISTS runs (
    run_hash TEXT PRIMARY KEY,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    status TEXT NOT NULL,
    config_json TEXT NOT NULL,
    manifest_json TEXT NOT NULL,
    data_hash TEXT NOT NULL,
    seed_root INTEGER NOT NULL,
    db_version INTEGER NOT NULL,
    bootstrap_seed INTEGER NOT NULL,
    walk_forward_spec_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
CREATE INDEX IF NOT EXISTS idx_runs_created ON runs(created_at DESC);

CREATE TABLE IF NOT EXISTS trades (
    run_hash TEXT NOT NULL,
    ts INTEGER NOT NULL,
    side TEXT NOT NULL,
    qty REAL NOT NULL,
    entry_price REAL,
    exit_price REAL,
    cost_bps REAL,
    borrow_cost REAL,
    pnl REAL,
    position_after REAL,
    FOREIGN KEY(run_hash) REFERENCES runs(run_hash)
);
CREATE INDEX IF NOT EXISTS idx_trades_run_ts ON trades(run_hash, ts);

CREATE TABLE IF NOT EXISTS equity (
    run_hash TEXT NOT NULL,
    ts INTEGER NOT NULL,
    equity REAL,
    drawdown REAL,
    realized_pnl REAL,
    unrealized_pnl REAL,
    cost_drag REAL,
    FOREIGN KEY(run_hash) REFERENCES runs(run_hash)
);
CREATE INDEX IF NOT EXISTS idx_equity_run_ts ON equity(run_hash, ts);

CREATE TABLE IF NOT EXISTS metrics (
    run_hash TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    value_type TEXT NOT NULL,
    phase TEXT,
    FOREIGN KEY(run_hash) REFERENCES runs(run_hash)
);
CREATE INDEX IF NOT EXISTS idx_metrics_run_key ON metrics(run_hash, key);

CREATE TABLE IF NOT EXISTS validation (
    run_hash TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    permutation_pvalue REAL,
    bootstrap_sharpe_low REAL,
    bootstrap_sharpe_high REAL,
    bootstrap_cagr_low REAL,
    bootstrap_cagr_high REAL,
    bootstrap_method TEXT,
    bootstrap_block_length INTEGER,
    bootstrap_jitter INTEGER,
    bootstrap_fallback INTEGER,
    FOREIGN KEY(run_hash) REFERENCES runs(run_hash)
);
CREATE INDEX IF NOT EXISTS idx_validation_run ON validation(run_hash);

CREATE TABLE IF NOT EXISTS features_cache (
    meta_hash TEXT PRIMARY KEY,
    spec_json TEXT NOT NULL,
    built_at INTEGER,
    rows INTEGER,
    columns INTEGER,
    digest TEXT
);

CREATE TABLE IF NOT EXISTS run_errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_hash TEXT NOT NULL,
    ts INTEGER NOT NULL,
    phase TEXT,
    error_code TEXT,
    message TEXT,
    stack_hash TEXT,
    FOREIGN KEY(run_hash) REFERENCES runs(run_hash)
);
CREATE INDEX IF NOT EXISTS idx_run_errors_run ON run_errors(run_hash);

CREATE TABLE IF NOT EXISTS phase_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_hash TEXT NOT NULL,
    phase TEXT NOT NULL,
    started_at INTEGER NOT NULL,
    ended_at INTEGER NOT NULL,
    duration_ms INTEGER NOT NULL,
    rows_processed INTEGER,
    extra_json TEXT,
    FOREIGN KEY(run_hash) REFERENCES runs(run_hash)
);
CREATE INDEX IF NOT EXISTS idx_phase_metrics_run ON phase_metrics(run_hash);

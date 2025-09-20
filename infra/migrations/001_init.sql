-- Initial schema (minimal; will evolve with domain models)
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    hash TEXT NOT NULL,
    status TEXT NOT NULL,
    stage TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    started_at INTEGER,
    completed_at INTEGER,
    error_code TEXT,
    error_message TEXT,
    config_json TEXT NOT NULL,
    seed INTEGER NOT NULL,
    metrics_summary_json TEXT,
    artifacts_manifest_sha TEXT
);

CREATE INDEX IF NOT EXISTS idx_runs_hash ON runs(hash);
CREATE INDEX IF NOT EXISTS idx_runs_created ON runs(created_at DESC);

CREATE TABLE IF NOT EXISTS presets (
    name TEXT PRIMARY KEY,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    config_json TEXT NOT NULL
);


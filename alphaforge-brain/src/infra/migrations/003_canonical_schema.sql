-- Canonical schema additions (Spec 005)
-- Additive-only to preserve existing data; uses new tables instead of ALTER operations.

-- features: canonical record of feature artifacts built per run
CREATE TABLE IF NOT EXISTS features (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_hash TEXT NOT NULL,
    spec_hash TEXT NOT NULL,
    rows INTEGER,
    cols INTEGER,
    digest TEXT,
    build_policy TEXT, -- JSON (chunk_size, overlap)
    cache_link TEXT,
    FOREIGN KEY(run_hash) REFERENCES runs(run_hash)
);
CREATE INDEX IF NOT EXISTS idx_features_run ON features(run_hash);
CREATE INDEX IF NOT EXISTS idx_features_spec ON features(spec_hash);

-- audit_log: immutable record of retention and artifact lifecycle events
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL, -- enum: pin, unpin, evict, rehydrate
    run_hash TEXT NOT NULL,
    actor TEXT,
    ts INTEGER NOT NULL, -- timestamp (epoch seconds or ns per app policy)
    details_json TEXT,
    FOREIGN KEY(run_hash) REFERENCES runs(run_hash)
);
CREATE INDEX IF NOT EXISTS idx_audit_run ON audit_log(run_hash);
CREATE INDEX IF NOT EXISTS idx_audit_event ON audit_log(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log(ts DESC);

-- runs_extras: optional extension columns aligning runs with canonical spec without altering existing table
CREATE TABLE IF NOT EXISTS runs_extras (
    run_hash TEXT PRIMARY KEY,
    config_hash TEXT,
    dataset_digest TEXT,
    latency_model TEXT,
    feature_timestamping TEXT,
    gap_policy TEXT,
    retention_state TEXT, -- enum: full, manifest-only, evicted, pinned, top_k
    pinned INTEGER, -- bool
    pinned_by TEXT,
    pinned_at INTEGER,
    primary_metric_name TEXT,
    primary_metric_value REAL,
    rank_within_strategy INTEGER,
    FOREIGN KEY(run_hash) REFERENCES runs(run_hash)
);
CREATE INDEX IF NOT EXISTS idx_runs_extras_config ON runs_extras(config_hash);
CREATE INDEX IF NOT EXISTS idx_runs_extras_dataset ON runs_extras(dataset_digest);
CREATE INDEX IF NOT EXISTS idx_runs_extras_metric ON runs_extras(primary_metric_value DESC);

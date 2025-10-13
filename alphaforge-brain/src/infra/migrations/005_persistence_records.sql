-- Governance persistence records (US2)
-- Stores schema-validated payloads for replayable artifacts.

CREATE TABLE IF NOT EXISTS persistence_records (
    record_id TEXT PRIMARY KEY,
    schema_version TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    source_component TEXT NOT NULL,
    validation_status TEXT NOT NULL,
    migration_history_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_persistence_records_component
    ON persistence_records(source_component);

CREATE INDEX IF NOT EXISTS idx_persistence_records_created
    ON persistence_records(created_at DESC);

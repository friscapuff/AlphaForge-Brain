-- Initial baseline objects only. Core domain tables are defined in subsequent migrations.

CREATE TABLE IF NOT EXISTS presets (
    name TEXT PRIMARY KEY,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    config_json TEXT NOT NULL
);

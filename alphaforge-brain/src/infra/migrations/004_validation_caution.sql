-- Phase 6: Migration tooling additions
-- Add validation caution fields and trade model version injection target columns to runs_extras

-- SQLite doesn't support IF NOT EXISTS for ADD COLUMN; this migration is applied once.
-- It is safe to run exactly once due to our schema_migrations tracking.

ALTER TABLE runs_extras ADD COLUMN validation_caution INTEGER; -- 0/1/null
ALTER TABLE runs_extras ADD COLUMN validation_caution_metrics TEXT; -- JSON-encoded list
ALTER TABLE runs_extras ADD COLUMN trade_model_version TEXT; -- e.g., "2"

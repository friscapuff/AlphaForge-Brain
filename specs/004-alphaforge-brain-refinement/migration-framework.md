# Migration Framework (FR-100, FR-150)

Status: Planning Complete (Gate 0)

Purpose: Define how database schema migrations are authored, versioned, loaded, and verified to prevent schema drift without explicit migration scripts.

## File Layout
- Package migrations directory (Python importable for runtime use):
  - `alphaforge-brain/src/infra/migrations/`
    - `001_init.sql` (present)
    - `002_<slug>.sql`
    - `...`
- Optional external companion for local dev (not used at runtime): `scripts/migrations/` for utilities.

## Naming & Ordering
- Filenames: zero-padded increasing integers, underscore, slug: `NNN_description.sql`.
- Migration version = integer parsed from filename.
- Head version = max(NNN) discovered in package.

## Loader & Execution
- Use `importlib.resources` to enumerate and read `.sql` files from `infra.migrations` package.
- Execute sequentially from version 1 → head against SQLite connection in a single transaction per file.
- Maintain a `meta` table with `schema_version` (integer) and `applied_at` timestamps.

## Verification (FR-150)
- Compute canonical hash of concatenated normalized SQL (strip comments/whitespace lines). Persist head hash in code constant and optionally in `meta` table.
- CI step compares expected head version/hash vs enumerated files; fails on mismatch or missing file.
- Runtime guard: if DB `schema_version` < code head, apply forward migrations; if `schema_version` > code head, abort with PERSIST_MIGRATION_MISSING.

## Cross-Refs
- Spec FR-100, FR-150
- Plan: package-level migration loader already added for 001.
- Tasks: T092 (scaffold), T109, T153 (CI integration)

---
Generated: 2025-09-24

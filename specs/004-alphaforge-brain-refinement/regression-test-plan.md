# Regression Hash Test Plan (FR-130–132, FR-142)

Status: Planning Complete (Gate 0)

Purpose: Define golden-hash based tests to ensure deterministic outputs for chunked pipeline and DB replay.

## Tests
1. Chunked Feature Equivalence (FR-130/131)
   - Input: canonical dataset (NVDA_5y.csv) normalized dtypes.
   - Process: run feature build monolithic; capture content hash of resulting features DataFrame (row-wise stable canonicalization: to_parquet digest or json canonical digest).
   - Run with chunk mode enabled (size heuristic and 2 alternates); compare content hashes.
   - Acceptance: All hashes equal; seam_diff_max == 0 for overlapping windows.

2. SQLite Round-trip Replay (FR-142)
   - After a baseline run, persist to SQLite. Drop on-disk artifacts. Re-materialize from DB via read helpers. Compare hashes to original artifacts.
   - Acceptance: All artifact hashes equal; DB row count metrics match manifest.

3. Determinism Replay (FR-151 support)
   - Two identical runs produce identical DB rows and artifact hashes. Prefix-stability check for bootstrap distributions when trials differ.

## Canonicalization Rules
- JSON: json.dumps(obj, sort_keys=True, separators=(",", ":")). UTF-8. sha256 of bytes.
- Parquet: Use content digest after write; or hash of arrow table canonical serialization.
- DataFrame CSV alternative: if used transiently, ensure index + dtypes preserved and LF newlines.

---
Generated: 2025-09-24

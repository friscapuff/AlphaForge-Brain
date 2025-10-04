# Research Notes: AlphaForge Brain Stability & Truthfulness

## Goals
- Deterministic, memory-safe pipeline with Arrow + chunking
- Canonical SQLite schema for provenance & fast retrieval
- Corporate actions: fully adjusted ingest
- Strict causality: .shift(1); execution at next-bar open
- Seeded validations: bootstrap, permutation, walk-forward for CI gates
- Retention: last-50 full, top-5 per strategy full, manual pin; rehydrate for evicted blobs

## Pipeline Chunking & Arrow I/O
- Chunk size heuristic: start with 1–5M rows per chunk (bounded by 1.5 GB CI cap); backpressure on memory sampler.
- Overlap window: parameterized (e.g., max lookback L) to avoid boundary effects. Verify hash-equivalence with monolithic run.
- Arrow IPC streaming: prefer feather/v2; Parquet with row groups tuned to chunk size for feature stores.

## Determinism & Hash Canonicalization
- Seed tree: seed_root → (data, features, execution, validation) scopes; derive via stable hash of config.
- JSON canonicalization: orjson with sorted keys and UTF-8; stable float formatting documented.
- Stable sort: explicit ordering for joins/aggregations; avoid parallel nondeterministic reducers.

## Corporate Actions Ingest
- Apply split/dividend adjustments upstream; store only adjusted series; persist factors_digest; dataset digest incorporates policy.
- Validation: re-ingest idempotency checks; digest equality; missing data → explicit error.

## Causality & Execution Model
- Features/signals: computed on bar close and shifted by one.
- Fills: next session open; halts/holidays → defer to next available open; no intra-bar fills.
- Costs: slippage + fees on entry/exit; documented in manifest.

## Validation Methods
- Bootstrap: 500 trials @95% CI; block_length tuned to preserve dependence; jitter controlled by seed.
- Permutation: 500 trials; strict determinism.
- Walk-forward: 5 splits; report aggregate metrics.
- CI width gate: assert within bounds; STRICT failure on nondeterminism.

## SQLite Schema & Migrations
- Tables: runs, trades, equity, features, validation, audit_log.
- Columns: include content hashes, seeds, timestamps, indices.
- Migrations: alembic scripts with checksum; CI fails on head mismatch.

## Retention Strategy & Rehydrate
- Keep last 50 full; top 5 per strategy full; manual pin wins over eviction.
- Demotion: manifest-only (SQLite rows + metrics retained; blobs evicted).
- Rehydrate: deterministic rebuild from inputs; mark in audit log.

## API Boundary & SSE
- Endpoints: submit, get, stream, list artifacts, pin/unpin, rehydrate.
- SSE events: seeded, ordered; include run_hash, phase, progress, timings.

## Observability
- Spans around chunk build, IO, validation; memory samples to correlate with chunk size.
- Overhead budget < 3%; benchmark with toggles.

## Risks & Mitigations
- Boundary effects on chunks → overlap & tests.
- Bootstrap runtime cost → cap trials in CI profile; parallel but stable ordering.
- Storage bloat → retention policy + compression.

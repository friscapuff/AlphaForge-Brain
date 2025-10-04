# Tasks – AlphaForge Brain Stability & Truthfulness (005-refine-alphaforge-brain)

## Status
- [x] Implementation complete (all enumerated tasks T001–T021 satisfied; tests green as of latest run)

This tasks list is dependency-ordered and immediately actionable. [P] marks tasks that can run in parallel. Map each commit to FR IDs (e.g., FR-101) and include failing tests first.

## TDD & Setup
- [x] T001: Initialize test scaffolds and fixtures [alphaforge-brain/tests]
  - Create base pytest config/markers, fixtures for seeded RNG, dataset loader stub, and temp SQLite.
  - Add helpers for content-hash (sorted JSON, UTF-8) and RSS sampling.
  - Done: Added fixtures freeze_time, random_seed_fixture, sqlite_tmp_path, json_canonical_dumps/content_hash_json, rss_sampler, arrow_roundtrip; added perf scaffold test at `alphaforge-brain/tests/perf/test_perf_scaffold.py` with `@pytest.mark.perf` and xfail/skip until FR-113.
  - Dep: none.
- [x] T002: Add CI job stubs for determinism, stress sweep, memory cap checks
  - Update CI to run pytest selections for FR-101/107/109/110 and report coverage.
  - Done: Added stub jobs in `.github/workflows/ci.yml` and placeholder scripts under `alphaforge-brain/scripts/ci/stubs/` for determinism, stress sweep, and memory cap; each uploads a JSON summary.
  - Dep: T001.

## Data Model & Migrations
- [x] T003: Create migrations for canonical tables (runs, trades, equity, features, validation, audit_log)
  - Implemented additive SQL migrations under `alphaforge-brain/src/infra/migrations/003_canonical_schema.sql` following data-model.md (features, audit_log, runs_extras); updated CI head tracking to `003_canonical_schema`.
  - Dep: T001.
- [x] T004: Add SQLAlchemy models and repositories
  - Added ORM package `alphaforge-brain/src/infra/orm/` with `base.py`, `session.py`, `models.py`, and `repositories.py`. Included models for runs, trades, equity, features, validation, audit_log and basic repositories (CRUD/list). Verified with a smoke create_all.
  - Dep: T003.

## Determinism & Hashing
- [x] T005 [P]: Tests for FR-101 determinism replay (unit + integration)
  - Two identical runs (sequential and parallel) → identical run_hash, artifact hashes, DB row digests.
  - Done: Added unit tests `alphaforge-brain/tests/unit/test_run_hash.py` and `alphaforge-brain/tests/unit/test_row_digest.py`; added integration tests `alphaforge-brain/tests/integration/test_manifest_hash_unified.py`. Validates order-independence and seed sensitivity; row digests are canonical.
  - Dep: T001.
- [x] T006: Implement run/artifact hashing and manifest writer
  - Stable hashing for artifacts; manifest with schema/api versions; integrate repositories.
  - Done: Implemented canonical run hash service `src/services/run_hash.py`; unified manifest hashing via `compute_composite_hash_from` in `src/models/manifest.py`, used by both `RunManifest.compute_composite_hash()` and `compute_run_hash`. Artifact collection is provided by `src/services/manifest.py::collect_artifacts`. Tests cover unification and determinism.
  - Notes: api_version/schema_version fields are not yet modeled; add later alongside API surface tasks (T016).
  - Dep: T004, T005.

## Pipeline Memory & Chunking
- [x] T007 [P]: Tests for FR-102 memory ceilings and chunk equivalence
  - Outputs equal monolithic; enforce CI ~1.5 GB cap; local warn 2.0 GB, soft-fail 3.0 GB.
  - Done: Added equivalence test `alphaforge-brain/tests/integration/test_chunk_equivalence.py` (SMA 10/50 across chunk sizes) and memory ceiling test `alphaforge-brain/tests/integration/test_memory_chunking.py` (2M rows, overlap 199). Memory test skips if RSS unsupported; asserts RSS < ~1.5 GB.
  - Added unit tests for adaptive chunk sizing `alphaforge-brain/tests/unit/test_choose_chunk_size.py`.
  - Dep: T001.
- [x] T008: Implement Arrow-based chunked feature pipeline with overlap and RSS sampling
  - Implemented deterministic chunk iterator and overlap handling via `src/services/chunking.py` and `domain/features/engine.py::build_features_chunked`.
  - Added adaptive helpers `estimate_row_size_bytes_from_df` and `choose_chunk_size` to target ~256 MB per chunk by default (cap 2,000,000 rows). Arrow I/O used by `infra/cache/features.py` persists chunked results when caching is enabled.
  - Dep: T004, T007.

## Corporate Actions Ingest
- [x] T009 [P]: Tests for FR-104 fully adjusted ingest
  - Done: Added unit tests `alphaforge-brain/tests/unit/test_adjustments.py` for factors digest determinism and split back-adjustment; added integration tests `alphaforge-brain/tests/integration/test_ingest_adjusted.py` asserting error on missing factors, dataset hash incorporates policy/factors, and idempotent re-ingest.
  - Dep: T001.
- [x] T010: Implement adjusted ingest and factors digest persistence
  - Done: Implemented `domain/data/adjustments.py` with policy, factors digest, and split adjustment; wired into `domain/data/ingest_nvda.py` and `domain/data/ingest_csv.py` with `adjustment_policy` and `adjustment_factors` parameters; metadata now records `adjustment_policy` and `adjustment_factors_digest`; cache keyed by (symbol,policy,factors_digest). All tests passing.
  - Dep: T004, T009.

## Causality & Execution
- [x] T011 [P]: Tests for FR-105/FR-106 causality and execution timing
  - STRICT fails on same-bar access; features at bar-close shift(1); fills at next-bar open; halts defer to next open; costs on entry/exit.
  - Done: Added unit/integration tests verifying guard behavior and wiring across features/strategy/orchestrator.
    - Unit: `alphaforge-brain/tests/unit/test_causality_guard.py`, `alphaforge-brain/tests/unit/test_causality_and_seed.py`.
    - Integration: `alphaforge-brain/tests/integration/test_causality_guard.py`, `alphaforge-brain/tests/integration/test_causality_wiring.py`,
      `alphaforge-brain/tests/integration/test_orchestrator_causality.py`.
    - Infra persistence: `alphaforge-brain/tests/infra/test_causality_persistence.py`.
  - Dep: T001.
- [x] T012: Implement causality guard and execution engine (next-open fills)
  - Implemented ContextVar-based guard with pandas shift(-k) instrumentation and context managers.
    - Guard: `alphaforge-brain/src/services/causality_guard.py` (CausalityGuard, CausalityMode, guard_context, pandas hooks).
    - Strategy runner wiring: `alphaforge-brain/src/domain/strategy/runner.py` accepts guard/guard_mode and runs features/strategy inside one guard context.
    - Orchestrator-wide single guard: `alphaforge-brain/src/domain/run/orchestrator.py` creates one guard for strategy, risk, and execution; STRICT raises, PERMISSIVE records.
    - Consolidated persistence: `alphaforge-brain/src/infra/persistence.py::record_causality_stats` writes metrics
      (causality_mode, future_access_violations) and updates manifest.causality_guard {mode, violations} once per run.
  - Execution engine: next-bar open fills, optional end-of-run flatten; fees and slippage applied on both sides.
    - File: `alphaforge-brain/src/domain/execution/simulator.py` (T+1 logic; _apply_costs and extended _apply_slippage_model).
  - Dep: T004, T011.

## Seeded Validations
- [x] T013 [P]: Tests for FR-107 bootstrap/permutation/walk-forward with CI defaults
  - Bootstrap 500 @95% CI, Permutation 500, Walk-forward 5 splits; deterministic outputs; persist metadata.
  - Done: Added unit tests `alphaforge-brain/tests/unit/test_validation_determinism.py` (seeded reproducibility across runs) and `alphaforge-brain/tests/unit/test_validation_gates.py` (CI width gate summarized via `block_bootstrap_gate_passed` flag without raising). Added integration test `alphaforge-brain/tests/integration/test_validation_persistence.py` verifying persisted validation payload (slim summary + params). Added infra test `alphaforge-brain/tests/infra/test_validation_metrics_persistence.py` asserting metrics rows (ci_low, ci_high, ci_width, mean, stdev, n, method, seed) are written deterministically. All tests pass under repeated execution validating hash & seed stability.
  - Dep: T001.
- [x] T014: Implement validation engines and persistence
  - Methods seeded; persist params/results; expose CI width checks.
  - Done: Implemented `src/domain/validation/runner.py` with permutation, block bootstrap, and walk-forward engines (seed-controlled) producing summary stats and CI width gating flag `block_bootstrap_gate_passed` (non-raising). Persistence wired via `src/infra/persistence.py::insert_validation` to store validation record plus per-metric rows in metrics table; orchestrator integration in `src/domain/run/orchestrator.py` stores slimmed validation payload and metrics. Added CI width threshold parameter in profile, deterministic RNG seeding, and summary structure (means, stdev, ci_low/high, width, gate flag). All related tests green.
  - Dep: T004, T013.

## API Surface (v0.1) & SDK
- [x] T015 [P]: Contract tests for API endpoints (contracts/api.md)
  - POST /runs, GET /runs/{id}, GET /runs/{id}/artifacts, GET /runs/{id}/events, POST pin/unpin/rehydrate.
  - Done: Added `tests/contract/test_api_contract_runs.py` covering deterministic run submission (idempotent hash), run detail, artifact listing & manifest fetch, SSE snapshot events (heartbeat + snapshot), and retention endpoints (pin/unpin/rehydrate) with placeholder behavior wired. Adjusted timeframe to canonical form, ensuring 200 responses. All contract tests passing.
  - Dep: T001, T006–T014.
- [x] T016: Implement FastAPI endpoints + SSE streaming
  - Include api_version/schema_version; deterministic responses; error model.
  - Done: Augmented `api/routes/runs.py` responses with `api_version`, `schema_version`, `content_hash`, pin/unpin/rehydrate endpoints implemented (in-memory retention state). Added content-hash computation using canonical hashing. SSE routes already present (`run_events.py`) integrated with validation summary aliasing. Contract keys surfaced deterministically.
  - Dep: T004, T006–T014, T015.
- [x] T016a: SDK package skeleton and client methods (FR-108)
  - Create `alphaforge-mind` thin client package (local-only for now) with methods: submit_run, get_run, stream_events, list_artifacts, pin, unpin, rehydrate; semantic version 0.1.0.
  - Done: Added `alphaforge-mind/src/client.py` (in-process or HTTP session injectable), `alphaforge-mind/src/alphaforge_mind_client.py` with `get_client` helper + fallback imports for dev. Deterministic SSE parsing implemented.
  - Dep: T015, T016.
- [x] T016b: Hello-run via SDK example and tests
  - Provide runnable example and tests verifying deterministic behavior using the SDK.
  - Done: Added `alphaforge-mind/tests/test_hello_run_sdk.py` spinning up FastAPI app with TestClient, injecting session into SDK client, asserting repeated submission yields identical run_hash and detail payload. Path injection used pending packaging. Test passing.
  - Dep: T016a.

## Retention & Rehydrate
- [x] T017 [P]: Tests for FR-112 retention policy
  - Scope: Last 50 full, top 5 per strategy full, manual pin persists; CI simulates non-destructive retention.
  - Done: Classification & state tagging tests (`test_retention_policy.py`), content hash/OpenAPI coverage, audit logging assertions (`test_retention_rehydrate_audit.py`), physical demotion + rehydrate cycle tests (`test_retention_physical_demotion.py`).
  - Dep: T001.
- [x] T017a: Expose configurable retention parameters (settings endpoint)
  - Done: Implemented GET/POST `/settings/retention` with bounds validation and immediate plan recompute + audit log event.
  - Dep: T017.
- [x] T017b: Extended negative & edge coverage
  - Added test asserting artifact_index excludes evicted files pre-rehydrate and restored after (`test_retention_extended_edges.py`).
  - Added retention settings idempotence + bounds validation test (same file).
  - Future: Cold-storage restore test (pending external backing store integration).
  - Dep: T017a.
- [x] T017c: Pin reclassification integration test
  - Implemented via `tests/integration/test_retention_rehydrate_audit.py` (includes PIN/UNPIN flow and audit log assertions).
  - Create enough runs to force demotion; select a demoted run, POST /runs/{h}/pin, assert retention_state transitions to `pinned` and run removed from `demote` set after plan recompute.
  - Include regression check: unpin -> plan recompute returns appropriate state (full/top_k or manifest-only depending on ranking/age).
  - Dep: T017.
- [x] T018: Implement retention engine, audit logging, rehydrate hook, cold storage & diff
  - Core (earlier): Planner, endpoints, dynamic settings, physical demotion, metrics endpoint.
  - Integrity: Audit hash chain (prev_hash/hash) + rotation (gzip) + integrity snapshot with threshold env `AF_AUDIT_ROTATE_BYTES`.
  - Size-Aware: Differential demotion with `max_full_bytes` + `budget_remaining` exposure.
  - Metrics: Per-state byte totals, total_bytes, audit rotation metrics (rotation_count, bytes + compression_ratio).
  - Planning: Dry-run plan (`GET /retention/plan`) and diff endpoint (`POST /retention/plan/diff`).
  - Cold Storage: Full offload/restore implementation (`infra/cold_storage.py`) supporting providers (`local`, `s3`, `gcs`) with env flags; integrated into demotion flow and new `/runs/{run_hash}/restore` endpoint.
  - OpenAPI: Added restore & diff paths; extended `RetentionMetrics.audit_rotation` and `RetentionPlanDiff` schema.
  - Tests: Added `test_retention_restore_and_diff.py` (diff + restore), extended rotation metrics assertions piggybacking on existing tests.
  - Docs: README section 15 (cold storage, diff, rotation metrics, enable flags) added.
  - Remaining (future enhancement ideas): asynchronous offload queue, tarball integrity hash, encryption at rest, pruning policy doc for rotated logs.
  - Dep: T004, T006, T016, T017.

## Stress, Benchmarks & CI Gates
- [x] T019 [P]: Stress test for FR-110 (parallel identical runs + bounded sweep)
  - Implemented `tests/stress/test_stress_parallel_and_sweep.py`:
    - Parallel identical submissions (4 threads) collapse to single run_hash & identical artifact digests.
    - Parameter sweep of 10 variants (5 seeds × 2 param combos) asserts unique run_hash per distinct config and artifact byte stability.
    - Re-run of first variant validates determinism (hash equality).
    - Digest verification re-hashes on-disk artifacts to match listed sha256.
  - Future extension: increase variant count to 20 in CI, add explicit memory sampler assertion hook if needed.
  - Dep: T001, T006–T014.
- [x] T020: Wire CI gates for FR-109/110 and cross-root integrity
  - Fail build on nondeterminism, contract drift, migration head mismatch, memory cap exceed, and cross-root import violations.
  - Dep: T002, T015, T019.
- [x] T020a: Performance benchmarks and CI thresholds (FR-113)
  - Implement tests/harness for observability overhead (<3%), bootstrap runtime (≤1.2× IID), memory sampler overhead (<1%); wire to CI as blockers.
  - Dep: T001, T013, T014.

## Documentation & Quickstart
- [x] T021 [P]: Update docs and quickstart
  - Added README anchors & Hello Run section linking to quickstart, plan, data model, retention (Section 15), OpenAPI artifacts.
  - Standardized terminology: "Hello Run (Quickstart)"; ensured minimal run example & determinism contract enumerated.
  - Cross-linked cold storage / retention features and clarified re-run idempotency.
  - Dep: T016–T020a.

## Parallelization Guidance
- [P] groups that can run concurrently:
  - Early tests: T005, T007, T009, T011, T013, T017
  - Implementations by area after ORMs: T008, T010, T012, T014
  - Later: T019 and T020a once hashing/validations exist; docs (T021) can trail CI gate work
- Sequential spine:
  - T003–T004 → T006–T014 → T016 → T016a → T016b → T018 → T020 → T020a → T021

## Task Agent Commands (examples)
- /tasks run T005;T007;T009;T011;T013;T017 [P]
- /tasks run T008;T010;T012;T014 [P]
- /tasks run T016;T016a;T016b
- /tasks run T019;T020a [P]
- /tasks run T020
- /tasks run T021 [P]

## Deferred / Optional Enhancements (not in baseline scope)
- Async cold-storage offload queue + retry backoff
- Tarball or Merkle tree integrity hash for artifact bundles
- Encryption-at-rest layer for cold storage blobs
- Expanded stress variants (N=20+) and memory sampler assertion hook
- Extended TOC generator to cover data-model and contracts auto-linking
- Packaging & publishing `alphaforge-mind` to PyPI with version pin tests
- Endpoint for historical retention plan snapshots & audit diff viewer
- Additional validation methods (e.g., stationary bootstrap) behind feature flag

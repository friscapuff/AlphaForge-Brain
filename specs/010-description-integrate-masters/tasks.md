# Tasks: Advanced Statistical Validation Integration

**Input**: Design documents from `/specs/010-description-integrate-masters/`
**Prerequisites**: plan.md, research.md, data-model.md, contracts/

## Execution Flow (main)
```
1. Confirm clarified assumptions inside design docs (histogram exposure, purge span, toggle surfaces)
2. Prepare shared test fixtures for deterministic validation datasets across Brain and Mind
3. Drive TDD: author contract + integration + unit tests covering every FR and user story
4. Implement domain models and services for Masters permutation, bias adjustments, cross-validation, and realism layers
5. Extend persistence, API/SSE contracts, CLI surfaces, and Mind UI/UX to consume the new validation payloads
6. Apply migrations, manifest upgrades, instrumentation, and promotion gating updates
7. Finish with performance checks, documentation, and quickstart validation
```

## Path Conventions
- **Brain**: `alphaforge-brain/src/`, `alphaforge-brain/tests/`, `scripts/`
- **Mind**: `alphaforge-mind/src/`, `alphaforge-mind/tests/`
- **Docs**: `specs/`, `docs/`, `openapi.*`, `README.md`

## Progress Log (2025-10-10 — 2025-10-11)
- Stabilized `GET /runs/{run_hash}` content hash calculation; the `tests/unit/test_content_hash_contract.py` suite now passes against the response payload.
- Updated coverage configuration to track installed packages (`api`, `domain`, `infra`, `services`, `models`, `lib`); full `poetry run pytest` run succeeds with 65.8% coverage, clearing the 29% gate.
- Completed Wave 3.3W (Masters services wrap): deterministic permutation seeding, enriched bias metadata, leakage-aware CPCV scheduler, ADV-derived realism fallback, and validation aggregator thresholds validated via full `poetry run pytest` (466 passed, 2 skipped, 11 xfailed, 4 xpassed).
- Mind contract refresh (T039) merged; `npm run test` in `alphaforge-mind` reports 47 passing files, 2 skipped, with the expected placeholder performance warning.
- Cleared lingering `src.*` import references across Masters validation services and domain models, unblocking bench instrumentation workstreams and restoring module loading in the Poetry environment.
- Validation instrumentation fixes landed: permutation histograms guard constant samples, structlog logger-name safety added, cross-validation span maths hardened, and benchmark harness rerun now captures full stage spans. Current SLA check fails due to elevated runtime (1543ms vs 34ms limit); tuning follow-up pending.
- Phase 3.5 polish (T043–T047) completed: property-based permutation suite merged, docs/quickstart/testing refreshed with validation smoke run, backfill playbook authored, and Masters retention policy published with gating table and waiver workflow. Latest bench smoke (`zz_artifacts/validation_smoke.json`) records total validation runtime of 1543 ms with module spans persisted for SLA tracking.

## Phase 3.1 · Setup
- [X] T001 Document clarified assumptions (histogram exposure = inline + artifact, default purge span = time-based embargo, toggles surfaced via CLI & Mind UI) in `specs/010-description-integrate-masters/research.md` decision log and close open questions.
- [X] T002 Seed deterministic validation fixtures in `alphaforge-brain/tests/fixtures/validation.py` (synthetic bar series, seeded optimizer config, expected seeds) for reuse across tests.
- [X] T003 [P] Add Mind-side fixture `alphaforge-mind/tests/fixtures/validationPayload.ts` mirroring contract examples for UI tests.

## Phase 3.2 · Tests First (TDD)
- [X] T004 [P] Create failing contract test `alphaforge-brain/tests/contract/test_runs_validation_v2.py` validating `GET /api/v1/runs/{id}` returns inline histogram summaries plus artifact refs (FR-008, FR-012).
- [X] T005 [P] Add SSE contract test `alphaforge-brain/tests/contract/test_validation_sse.py` ensuring `validation.update` streams segment payloads with correlation IDs (FR-008).
- [X] T006 [P] Add manifest contract test `alphaforge-brain/tests/contract/test_validation_manifest_v2.py` asserting schema version bump, module toggles, artifact hashes (FR-013, FR-014).
- [X] T007 [P] Acceptance scenario 1 integration test `alphaforge-brain/tests/integration/validation/test_permutation_significance.py` covering Masters permutation p-values and pass/fail gating (FR-001, FR-002).
- [X] T008 [P] Acceptance scenario 2 integration test `alphaforge-brain/tests/integration/validation/test_sharpe_bias_adjustments.py` for DSR/PSR calculations and storage (FR-004, FR-005).
- [X] T009 [P] Acceptance scenario 3 integration test `alphaforge-brain/tests/integration/validation/test_cross_validation_leakage.py` validating purged K-Fold & CPCV with time-based purge span default and asserting the 0.25 absolute / 20% relative Sharpe drop bias flag rule (FR-005, FR-006).
- [X] T010 [P] Acceptance scenario 4 integration test `alphaforge-brain/tests/integration/validation/test_execution_realism_alerts.py` covering cost/impact/capacity warnings and verifying guidance payload includes deltas, capacity ratio, and remediation text (FR-009).
- [X] T011 [P] Acceptance scenario 5 Mind integration test `alphaforge-mind/tests/integration/validation-view.spec.ts` asserting visualization of all new panels and correlation IDs (FR-011).
- [X] T012 [P] Brain unit tests `alphaforge-brain/tests/unit/validation/test_permutation_engine.py` asserting deterministic permutation batches and re-optimisation hooks (FR-001, FR-003).
- [X] T013 [P] Brain unit tests `alphaforge-brain/tests/unit/validation/test_bias_adjustments_math.py` verifying DSR/PSR formulas against reference values (FR-004, FR-005).
- [X] T014 [P] Brain unit tests `alphaforge-brain/tests/unit/validation/test_cross_validation_scheduler.py` for time-based purge-span calculation, CPCV fallback determinism, and bias flag threshold math (FR-005, FR-006).
- [X] T015 [P] Brain unit tests `alphaforge-brain/tests/unit/validation/test_execution_realism_report.py` covering aggregation, double-count avoidance, and required guidance elements (FR-009).
- [X] T016 [P] Brain unit tests `alphaforge-brain/tests/unit/cli/test_validation_config_flags.py` checking CLI/SDK toggles emit deterministic config metadata (FR-007, FR-014).
- [X] T017 [P] Mind unit tests `alphaforge-mind/tests/unit/components/ValidationOutputs.test.tsx` for permutation charts, bias cards, fold timelines, realism gauges, and toggle controls (FR-011).

## Phase 3.3 · Core Implementation

### Wave 3.3A · Domain & Persistence Foundations
- [X] T018 [P] (brain) Implement `PermutationValidationResult` model + repository helpers in `alphaforge-brain/src/domain/validation/masters/permutation_result.py` and register with persistence layer (FR-001, FR-013).
- [X] T019 [P] (brain) Implement `SharpeBiasAdjustment` data model in `alphaforge-brain/src/domain/validation/masters/bias_adjustment.py` (FR-004).
- [X] T020 [P] (brain) Implement `CrossValidationFold` representation with time-based purge span metadata in `alphaforge-brain/src/domain/validation/masters/cross_validation_models.py` (FR-006).
- [X] T021 [P] (brain) Implement `ExecutionRealismReport` model in `alphaforge-brain/src/domain/validation/realism/report.py` including fields for cost/impact deltas, capacity ratio, and remediation guidance (FR-009).
- [X] T022 [P] (brain) Extend `ValidationConfig` schema & serialization in `alphaforge-brain/src/models/validation_config.py` for per-module toggles and thresholds (FR-007, FR-014).
- [X] T028 (brain) Extend ORM/repository in `alphaforge-brain/src/infra/orm/models.py` & `alphaforge-brain/src/infra/repos/validation_repository.py` to persist new columns and metadata (FR-001, FR-004, FR-006, FR-009).

### Wave 3.3B · Services & Aggregation
- [X] T023 (brain) Build Masters permutation orchestrator with deterministic seed derivation and inline histogram summary emission in `alphaforge-brain/src/services/validation/masters_permutation.py` (FR-001, FR-003).
- [X] T024 (brain) Implement DSR/PSR computation service in `alphaforge-brain/src/services/validation/bias_adjustments.py` and wire into validation pipeline (FR-004, FR-005).
- [X] T025 (brain) Implement purged K-Fold + CPCV scheduler using time-based embargo defaults and applying the 0.25 absolute / 20% relative Sharpe drop bias rule in `alphaforge-brain/src/services/validation/cpcv_scheduler.py` (FR-005, FR-006).
- [X] T026 (brain) Integrate execution realism overlays with existing cost/impact models in `alphaforge-brain/src/services/validation/realism.py`, populating guidance deltas, capacity ratio, and remediation recommendations (FR-009).
- [X] T027 (brain) Update validation aggregator in `alphaforge-brain/src/services/validation/aggregator.py` to combine module outputs, compute `validation_significance`, and enforce promotion gating flags (FR-002, FR-010, FR-015).
- [X] T029 (brain) Update manifest writer `alphaforge-brain/src/services/manifest.py` to emit validation schema v2, artifact hashes, and config metadata (FR-008, FR-013, FR-014, FR-016).
	- Schema v2 manifest metadata now emitted via placeholder validation payloads (2025-10-10); pending aggregator wiring under T027.
- [X] T030 (brain) Update `GET /api/v1/runs/{id}` handler in `alphaforge-brain/src/api/routes/v1_backtests.py` to return inline histogram summaries alongside artifact references and bias/cross-validation/realism payloads (FR-008, FR-012).
	- Schema v2 payload exposed via dedicated `validation_*` fields while legacy summary preserved for compatibility (2025-10-10); pending real data wiring from aggregators under T023–T027.
	- `RunDetailResponse` content hash now derived from the serialized response, keeping client hash contracts stable (2025-10-10).
- [X] T031 (brain) Update SSE streamer `alphaforge-brain/src/api/routes/run_events.py` to broadcast sectioned updates with correlation IDs (FR-008).
	- Snapshot now mirrors schema v2 metadata plus legacy summary for streaming clients (2025-10-10).
- [X] T032 (brain) Extend CLI + SDK surfaces (`alphaforge-brain/scripts/validation/show_summary.py`, `alphaforge-brain/src/services/cli/validation_flags.py`) to expose module toggles and print rich validation summaries (FR-007, FR-014).
	- Added manifest-driven summary CLI showing module toggles, segments, bias, cross-validation, and realism metrics (2025-10-10).

### Wave 3.3C · Mind Integration
- [X] T033 (mind) Update API client & state adapters in `alphaforge-mind/src/services/api/backtests.ts` and related stores to map new validation payloads (FR-011).
- [X] T034 (mind) Implement validation view components & toggle UI in `alphaforge-mind/src/pages/backtest/ValidationView.tsx` and new components under `alphaforge-mind/src/components/validation/`, rendering execution guidance deltas/capacity/remediation copy (FR-009, FR-011).

## Phase 3.4 · Integration
- [x] T035 Create Alembic migration `alphaforge-brain/src/infra/alembic/versions/XXXX_validation_schema_v2.py` adding nullable columns, default schema version, and JSON1 guards (FR-001, FR-004, FR-006, FR-009).
	- Implemented Python-backed migration runner (`infra/alembic/runner.py`) and first revision `20251010001_validation_schema_v2.py` with JSON1 enforcement, validation table recreation, and runs schema bump; legacy persistence upgraded to emit schema version 2 rows.
- [x] T036 Update manifest hash + replay tooling in `alphaforge-brain/src/services/hashing/validation_signature.py` to account for new sections while keeping historical runs neutral (FR-013, FR-016).
- [x] T037 Update promotion/retention policies in `alphaforge-brain/src/services/retention/policies.py` to block auto-promotion when significance/realism fail (FR-010).
- [x] T038 Add observability instrumentation (timings, resource usage) for validation modules in `alphaforge-brain/src/infra/observability/tracing.py` and structlog config (FR-015).
- [x] T039 Refresh TypeScript contract types & API client mocks across the Mind validation surface and unit fixtures (FR-011, FR-012).
	- Updated Mind schema adapters (`alphaforge-mind/src/services/api/backtests.ts`), validation components, and fixtures; vitest suite (`npm run test`) now passes with new contract coverage (47 passing files, 2 skipped).
	- Manifest signature now normalizes config/modules/caution metadata and persists deterministic hashes covering Masters payloads; replay tooling exercises new validation artifacts (2025-10-11).
	- Retention gating now inspects schema v2 manifest metadata and realism status so failed validation runs remain manifest-only unless pinned; extended tests cover nested metadata (2025-10-11).
	- Validation tracing logs now include CPU/memory deltas plus process/thread IDs and persist peak deltas for SLA tracking; structlog emits logger names for easier correlation (2025-10-11).
- [x] T040 Regenerate OpenAPI spec (`openapi.json`, `openapi.html`) and update API docs to include new schemas and examples (FR-012).
	- FastAPI schema exported via `scripts/dev/export_openapi.py` (structlog-safe); canonical YAML replaced with generated contract and rebundled (`npm run bundle:api`, `deref:api`, `docs:api`). Validation v2 payload fields now documented across JSON, deref JSON, and HTML artifacts.
- [X] T041 Extend `scripts/bench/perf_run.py` to capture validation stage timings and write SLA guard rails for Masters modules (FR-015).
	- Harness updated to persist validation spans across all modules; histogram guardrails and structlog safety ensure runs complete without instrumentation errors.
	- `poetry run python scripts/bench/perf_run.py --iterations 1 --warmup 0` captures stage timings and writes `zz_artifacts/perf_latest.json`. Current SLA check flags total duration (1543 ms > 34 ms limit); performance tuning queued separately.
- [X] T042 Author decision record `docs/decisions/validation_schema_v2.md` documenting unified `validation_results` table rationale and purge-span assumption (governance follow-up).
	- Decision record refreshed 2025-10-11 with unified-table rationale, purge-span policy, and latest SLA benchmark (1543 ms vs 34 ms limit) to guide follow-up tuning.

## Phase 3.5 · Polish
- [X] T043 [P] Add Hypothesis-based property tests for permutation distribution sanity in `alphaforge-brain/tests/property/validation/test_permutation_distribution.py` (FR-001).
	- Property suite verifies histogram bin counts, percentile ordering, p-value bounds, and constant-return collapse using Hypothesis strategies; run via `poetry run pytest alphaforge-brain/tests/property/validation/test_permutation_distribution.py --no-cov`.
- [x] T044 [P] Update README, Quickstart, and Mind docs (`README.md`, `alphaforge-mind/README.md`, `specs/010-description-integrate-masters/quickstart.md`) with final instructions and toggle guidance (FR-011, FR-014).
	- Root README quick actions, Mind README surface overview, and quickstart benchmark section now cover Masters toggles, property test flow, and current SLA deficit (1543 ms vs 34 ms).
- [x] T045 Execute quickstart validation run and capture artifacts in `zz_artifacts/validation_smoke.json`, updating `TESTING.md` with results (FR-001–FR-011 coverage proof).
	- `poetry run python scripts/bench/perf_run.py --iterations 1 --warmup 0 --keep-artifacts --output zz_artifacts/validation_smoke.json` produced run `b5a64f82…`. Smoke JSON records Masters spans (permutation 1243 ms, CPCV 8 ms, bias 11 ms, realism 113 ms) and SLA violations (total 1543 ms vs 34 ms). `TESTING.md` documents artifact locations and current manifest placeholder gap.
- [x] T046 [P] Draft migration/backfill guide `docs/operations/validation_backfill.md` outlining optional historical enrichment workflow (FR-016).
	- Playbook covers prerequisites, SQL to discover schema v1 runs, `create_or_get` replay snippet, CLI verification steps, SLA notes (1543 ms vs 34 ms limit), and rollback guidance referencing `validation_schema_v2` decision record.
- [x] T047 Close loop with retention & data teams by updating `docs/governance/retention_policy.md` to reflect Masters validation gates and obtain sign-off.

## Dependencies
- T002 → prerequisite for T004–T016.
- T003 → prerequisite for T011, T017, T033–T034, T039.
- T004–T017 (tests) must complete before corresponding implementation tasks T018–T034.
- T018–T022 unblock services T023–T027.
- T028 depends on T018–T022; T029 depends on T028.
- T030 depends on T029; T031 depends on T023–T025; T032 depends on T022 & T029.
- T033 depends on T030; T034 depends on T033 & T031.
- T035 depends on T028; T036 depends on T029; T037 depends on T027; T038 depends on T023–T027; T039 depends on T033–T034; T040 depends on T030–T031; T041 depends on T023–T027; T042 depends on T035–T036.
- Polish tasks T043–T047 require completion of all integration tasks (T035–T042).

## Parallel Execution Examples
```
# After fixtures are ready, run Brain contract tests together
specify tasks run --feature 010-description-integrate-masters T004 T005 T006

# Execute Mind-facing test wave in parallel once fixtures exist
specify tasks run --feature 010-description-integrate-masters T011 T017 T039
```

## Validation Checklist
- [x] All contracts mapped to explicit test tasks (T004–T006, T011)
- [x] Each data-model entity has a dedicated model implementation task marked [P] (T018–T022)
- [x] Tests precede implementations across Brain and Mind (T004–T017 before T018–T034)
- [x] Parallel tasks only touch disjoint files
- [x] Assumptions (inline histograms + artifacts, time-based purge span, dual toggle surfaces) documented via T001 and enforced in tasks
- [x] Migration, instrumentation, documentation, and validation polish steps scheduled (T035–T047)

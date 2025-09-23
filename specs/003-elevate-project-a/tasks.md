# Tasks: Elevate Project A to Truthful Backtest Simulator (Truthful Run Foundation)

**Feature Dir**: `specs/003-elevate-project-a/`  
**Input Artifacts**: plan.md, research.md, data-model.md, quickstart.md, contracts/ (runs.post.json, runs.get.json, runs.events.sse.md, versioning.md)
**Tech Stack**: Python 3.11, FastAPI, Pydantic, numpy/pandas, matplotlib, pytest, mypy (strict), ruff

## Execution Principles
- Test-first (contract & integration) before implementation
- Determinism (hashes, seeds, float precision) enforced early
- Each task atomic & file-scoped when parallel [P]
- MUST cover FR-001..FR-049 (current scope; FR-049 future placeholder only)

## Phase 3.1: Setup & Tooling
- [x] T001 Create `src/models/__init__.py` & base typing module `src/models/base.py` (dataclass/pydantic config: frozen, validate_assignment) – prepares model namespace.
- [x] T002 Configure deterministic float & RNG bootstrap module `src/lib/determinism.py` (apply numpy/pandas print options, set global seed function) + unit test skeleton.
- [x] T003 Add test scaffolding: create directories `tests/contract`, `tests/integration`, `tests/unit`, `tests/perf` with `__init__.py` files.
- [x] T004 Add `pyproject.toml` updates (if needed) to ensure mypy strict & ruff config enforce no new ignores (reference plan.md). (Skip if already configured – verify.)
- [x] T005 [P] Add `scripts/dev/run_mypy.sh` & `scripts/dev/run_ruff.sh` for CI gating (simple shell or PowerShell wrappers) + README note.
- [x] T006 Implement `src/lib/hash_utils.py` for canonical JSON serialization & run/config hashing (FR-015, FR-024, FR-041) + placeholder unit tests.

## Phase 3.2: Contract & High-Level Tests (Fail First)
- [x] T007 [P] Contract test POST /runs -> `tests/contract/test_runs_post.py` (assert schema keys: run_id, run_hash, status; idempotent re-post returns same run_hash) using `runs.post.json` contract.
- [x] T008 [P] Contract test GET /runs/{id} -> `tests/contract/test_runs_get.py` (artifacts array with name, sha256, size; status transitions) using `runs.get.json`.
- [x] T009 [P] Contract test SSE events -> `tests/contract/test_runs_events_sse.py` (heartbeat ≤15s simulated, phase ordering, terminal event) using `runs.events.sse.md`.
- [x] T010 [P] Contract test versioning invariants -> `tests/contract/test_versioning.py` (OpenAPI version equals package version; additive changes only) using `versioning.md`.
- [x] T011 Integration test deterministic replay -> `tests/integration/test_deterministic_replay.py` (same config => identical run_hash + artifact hashes) covers FR-001, FR-015, FR-023, FR-024, FR-041.
- [x] T012 Integration test causality guard strict vs permissive -> `tests/integration/test_causality_guard.py` (intentional future access triggers violation in STRICT, logs count in PERMISSIVE) FR-005, FR-006, FR-028.
- [x] T013 Integration test execution + costs -> `tests/integration/test_execution_costs.py` (ledger reconciliation: trade -> equity -> pnl components) FR-007..FR-011, FR-039.
- [x] T014 Integration test permutation validation -> `tests/integration/test_permutation_validation.py` (N trials produce stable distribution & p-value; skip case N=0 placeholders) FR-019..FR-022, FR-040, FR-042, FR-043.
- [x] T015 Integration test walk-forward segmentation & robustness -> `tests/integration/test_walk_forward.py` (segment boundaries monotonic, aggregated metrics present: oos_consistency_score, robustness_score) FR-046..FR-048.
- [x] T016 Integration test robustness reporting composite -> `tests/integration/test_robustness_reporting.py` (presence & deterministic rounding of p_value, extreme_tail_ratio, robustness_score after enabling walk-forward) FR-043, FR-047.
- [x] T017 Integration test strategy registry metadata optional -> `tests/integration/test_strategy_registry_metadata.py` (if provided -> manifest fields appear) FR-045.
- [x] T018 Integration test anomaly counters & snapshot -> `tests/integration/test_anomalies_snapshot.py` (include_anomalies=true returns subset) FR-036.

## Phase 3.3: Model Layer (Entities) [Write After Tests Exist]
Status: COMPLETE (all models implemented; mypy clean; deterministic helpers in `RunConfig` & manifest; validators enforce invariants).
- [x] T019 [P] Implement DatasetSnapshot model -> `src/models/dataset_snapshot.py` FR-001..FR-003.
- [x] T020 [P] Implement FeatureSpec model -> `src/models/feature_spec.py` FR-004, FR-005.
- [x] T021 [P] Implement StrategyConfig model -> `src/models/strategy_config.py` FR-004.
- [x] T022 [P] Implement ExecutionConfig model -> `src/models/execution_config.py` FR-007, FR-009.
- [x] T023 [P] Implement CostModelConfig model -> `src/models/cost_model_config.py` FR-008, FR-039.
- [x] T024 [P] Implement ValidationConfig model -> `src/models/validation_config.py` FR-019..FR-022.
- [x] T025 [P] Implement WalkForwardConfig model -> `src/models/walk_forward_config.py` FR-046..FR-048.
- [x] T026 [P] Implement RunConfig aggregate model -> `src/models/run_config.py` FR-015, FR-029.
- [x] T027 [P] Implement Trade model -> `src/models/trade.py` FR-010.
- [x] T028 [P] Implement EquityBar model -> `src/models/equity_bar.py` FR-011.
- [x] T029 [P] Implement ValidationResult model -> `src/models/validation_result.py` FR-020, FR-042, FR-043.
- [x] T030 [P] Implement WalkForwardSegment & WalkForwardAggregate models -> `src/models/walk_forward.py` FR-046..FR-048.
- [x] T031 [P] Implement RunManifest & ArtifactDescriptor models -> `src/models/manifest.py` FR-015, FR-023, FR-024, FR-031, FR-035.
- [x] T032 [P] Implement SummarySnapshot model -> `src/models/summary_snapshot.py` FR-013, FR-026, FR-036.
- [x] T033 [P] Implement CausalityViolationMetric model -> `src/models/causality_violation.py` FR-006.

## Phase 3.4: Services & Core Logic
Status: COMPLETE (all service modules implemented; pending type hygiene gating before API exposure).
- [x] T034 Implement feature registry loader & shift enforcement -> `src/services/features.py` (apply global +1 shift) FR-004, FR-005.
- [x] T035 Implement causality guard proxy & context manager -> `src/services/causality_guard.py` FR-006, FR-028.
- [x] T036 Implement execution engine (position application, lot rounding) -> `src/services/execution.py` FR-007, FR-009, FR-010.
- [x] T037 Implement cost model application (slippage, fees, borrow) -> `src/services/costs.py` FR-008, FR-039.
- [x] T038 Implement ledger → equity curve aggregator -> `src/services/equity.py` FR-011.
- [x] T039 Implement metrics calculator (returns, drawdown, Sharpe, turnover, win rate) -> `src/services/metrics.py` FR-012, FR-013.
- [x] T040 Implement permutation engine (seed list, structural shuffle, ordering) -> `src/services/permutation.py` FR-019, FR-040, FR-042, FR-043.
- [x] T041 Implement walk-forward segmenter & parameter optimizer -> `src/services/walk_forward.py` FR-046, FR-048.
- [x] T042 Implement robustness scoring aggregator (p_value, tails, OOS stability composite) -> `src/services/robustness.py` FR-047.
- [x] T043 Implement manifest writer (hashing, artifact hashing) -> `src/services/manifest.py` FR-015, FR-023, FR-024, FR-031, FR-035, FR-041.
- [x] T044 Implement summary snapshot generator & SSE serialization -> `src/services/snapshots.py` FR-013, FR-018, FR-020a, FR-036, FR-047.
- [x] T045 Implement anomaly detector (gaps, duplicates, holiday classification) -> `src/services/validation.py` FR-002, FR-003, FR-030.
- [x] T046 Implement strategy registry metadata recorder (optional) -> `src/services/strategy_registry.py` FR-045.
- [x] T047 Implement run orchestrator (phase progression, error handling) -> `src/services/orchestrator.py` FR-026, FR-033.
- [x] T048 Implement SSE event emitter (heartbeat scheduler) -> `src/services/events.py` FR-018, FR-032.
- [x] T049 Implement API request validators (pydantic schemas) -> `src/services/api_validation.py` FR-017, FR-019..FR-022.

## Phase 3.4H: Type Hygiene Gate (Path A)
Rationale: Ensure static analysis signal quality before public API & persistence wiring to prevent debt compounding.
- [x] T080 Add `tests/conftest.py` to fix PYTHONPATH import (`src`) & re-run baseline. (Verified path already correct.)
- [x] T081 Remove unused `# type: ignore` comments (enumerate & delete) across repo.
- [x] T082 Annotate test functions (`-> None`) & add missing generics (dict[str, Any]).
- [x] T083 Add precise type annotations to services (`features.model_post_init`, `execution.generate_trades` `ts: datetime`, events/validation dict generics).
- [x] T084 Introduce `types-toml` (or ignore) decision & apply (install stubs or add mypy config ignore). (Decision: no additional stubs needed.)
- [x] T085 Enforce zero mypy errors CI gate (update scripts if needed) & record hash of clean state in `typing_timing.json` extension.
- [x] T086 Update `spec.md` decision log & `plan.md` dependencies to reflect hygiene gate completion requirement before Phase 3.5.

## Phase 3.5: API Layer (begins after Phase 3.4H complete)
- [x] T050 Implement POST /runs endpoint -> `src/api/routes/runs.py` FR-016 (idempotency), FR-015, FR-017.
- [x] T051 Implement GET /runs/{id} endpoint -> `src/api/routes/runs.py` FR-017, FR-023.
- [x] T052 Implement SSE /runs/{id}/events stream endpoint -> `src/api/routes/run_events.py` FR-018, FR-032.
- [x] T053 Integrate OpenAPI version injection -> `src/api/app.py` (dynamic importlib.metadata + fallback) FR-031.
- [x] T054 Add dependency wiring (FastAPI app factory) -> `src/api/app.py` (include router, SSE headers) FR-018, FR-032.

## Phase 3.6: Persistence & Artifacts
- [x] T055 Implement artifact writer utilities (parquet, json, plots) -> `src/lib/artifacts.py` FR-014, FR-015, FR-023. (Completed: equity/trades parquet, json writer, artifact index)
- [x] T056 Implement deterministic plotting module -> `src/lib/plot_equity.py` FR-014, FR-041. (Completed: fixed rcParams, no timestamp embedding)
- [x] T057 Implement artifact manifest finalization & replay test fixture -> `tests/integration/fixtures_manifest.py` FR-024. (Completed: model-backed loader + composite hash integrity assertion)

## Phase 3.7: Additional Tests & Edge Cases
- [x] T058 [P] Unit tests for cost model rounding & order -> `tests/unit/test_costs.py` FR-008, FR-039.
- [x] T059 [P] Unit tests for permutation invariants (gap preservation) -> `tests/unit/test_permutation_invariants.py` FR-042.
- [x] T060 [P] Unit tests for walk-forward split validation -> `tests/unit/test_walk_forward_splits.py` FR-048.
- [x] T061 [P] Unit tests for robustness scoring weight math -> `tests/unit/test_robustness_scoring.py` FR-047.
- [x] T062 [P] Unit tests for hashing determinism (config_hash/run_hash) -> `tests/unit/test_hashing.py` FR-015, FR-024, FR-041.
- [x] T063 [P] Unit tests for causality guard violations -> `tests/unit/test_causality_guard.py` FR-006.
- [x] T064 [P] Unit tests for manifest schema completeness -> `tests/unit/test_manifest_schema.py` FR-015, FR-023.
- [x] T065 [P] Unit tests for SSE event ordering & heartbeat interval -> `tests/unit/test_sse_events.py` FR-018, FR-026, FR-032.
- [x] (Infra) Apply deterministic time fixture (`freeze_time`) to timestamp-sensitive tests (manifest, SSE events) ensuring exact-match assertions.
- [x] (Infra) Parameterize walk-forward segmentation tests to cover multiple stride/warmup scenarios & insufficient-total edge case (zero segments).
- [x] (Infra) Introduce centralized `random_seed_fixture` removing scattered seeding in permutation / bootstrap tests.

## Phase 3.8: Performance & Determinism Validation
- [x] T066 Performance test baseline run (<5s) -> `tests/perf/test_baseline_run.py` FR-012, FR-026.
- [x] T067 Performance test permutation N=100 (<30s) -> `tests/perf/test_permutation_perf.py` FR-040, FR-044.
- [x] T068 Performance test guard overhead (<1%) -> `tests/perf/test_guard_overhead.py` FR-006.

## Phase 3.9: Polish & Documentation
- [x] T069 [P] Update quickstart with any new CLI or config nuance (if changed) -> `specs/003-elevate-project-a/quickstart.md` FR-047. (Completed: anomaly_counters guarantee & replay verification section added.)
- [x] T070 [P] Add README section "Robustness & Validation" linking to research rationale. (Added Section 7.b covering validation layers & guarantees.)
- [x] T071 [P] Generate OpenAPI snapshot & diff test -> `tests/contract/test_openapi_diff.py` FR-031. (Additive diff test + minimal snapshot.)
- [x] T072 Add CHANGELOG entries for new modules & endpoints. (0.3.1-dev updated; robustness, diff test, script placeholder.)
- [x] T073 Add developer doc `docs/architecture/truthful_run.md` summarizing flow. (Created with anchors & pipeline diagram.)
- [x] T074 Refactor duplication (if any) & ensure mypy clean (no new suppressions). (Scan performed; no action required.)
- [x] T075 Final deterministic replay smoke script -> `scripts/verify_replay.py` (run twice, compare hashes) FR-024. (Implemented.)

## Phase 3.10: Future Placeholders (Non-Executable Now)
- [x] T076 Document adaptive validation placeholder structures in validation.json (future_methods) FR-049. (Added future_methods placeholder will be injected when validation artifact assembled; spec clarified—no runtime logic yet.)
- [x] T077 Stub distributed permutation backend interface -> `src/services/permutation_backends.py` FR-044 (deferred) – ensure no execution path yet. (Protocol + DEFAULT_BACKEND None stub created.)
- [x] T078 Stub strategy registry governance expansion doc -> `docs/roadmap/strategy_registry.md` FR-045. (Roadmap placeholder with governance outline added.)

## Dependencies Summary
- Setup (T001-T006) precedes all.
- Contract & integration tests (T007-T018) must exist and fail prior to models (T019+).
- Models (T019-T033) unblock services (T034-T049).
- Services (T034-T049) complete; Type Hygiene Gate (T080-T086) must pass (zero mypy errors) before API layer (T050-T054) commences.
- Manifest & artifacts (T055-T057) required before replay & robustness integration tests fully pass.
- Walk-forward (T041, T030, T060) feeds robustness scoring (T042, T061).
- SSE emitter (T048) required for event tests (T065) to pass.
- Performance tests (T066-T068) after core implementation passes functional tests.
- Polish tasks (T069-T075) last; placeholders (T076-T078) non-blocking.

## Parallel Execution Guidance
Example early parallel batch after setup (all independent files):
```
T007, T008, T009, T010 (contract tests)
T011, T012, T013, T014, T015, T016, T017, T018 (integration tests)
```
Model layer parallel batch:
```
T019-T033 (distinct model files)
```
Service layer selective parallel (avoid orchestrator until dependencies ready):
```
T034, T035, T036, T037, T038, T039, T040 (independent) then
T041 (depends on metrics + execution), T042 (depends on permutation + walk-forward), T043, T044, T045, T046
```

## Validation Checklist
- [x] All contracts mapped to tests (T007-T010, T071 diff) ✔
- [x] All entities mapped (T019-T033) ✔
- [x] Walk-forward & robustness tasks present (T015, T016, T025, T030, T041, T042, T060, T061) ✔
- [x] Determinism hashing & float policy tasks present (T002, T006, T062) ✔
- [x] Performance guard tasks present (T066-T068) ✔
- [x] Future adaptive placeholder (T076) ✔
- [ ] Type hygiene gate tasks (T080-T086) pending
	* Current status: COMPLETED in codebase (freeze_time + RNG centralization occurred post-hygiene; checklist not yet toggled here originally).

## Notes
- Keep tasks atomic; commit after each. Bundle 3-5 together only if its logical to do so. Provide clear commit decriptions.
- Ensure failing state of tests before implementation (capture snapshot).
- Do not implement future placeholders beyond minimal stubs.
- Weights for robustness_score documented in research; adjust only with spec change.

*Generated: 2025-09-22 — Updated 2025-09-23 with deterministic test infrastructure (freeze_time, RNG fixture, walk-forward parameterization) and README section 7.a refresh.*

### Recent Infrastructure Rationale (2025-09-23)
| Enhancement | Problem Previously | Resolution | Benefit |
|-------------|-------------------|-----------|---------|
| `freeze_time` fixture | Tests compared timestamp prefixes risking flakes & partial assertions | Subclasses `datetime` in project modules for stable aware instant | Full equality assertions; zero flake baseline |
| Central RNG seed fixture | Ad-hoc `seed=` literals duplicated across tests | Single fixture returns canonical seed & seeds `random` | Easier to adjust global test determinism policy |
| Walk-forward test parameterization | Single scenario under-tested edge cases | Param matrix + algorithmic expected count derivation | Higher coverage, clearer regression signal |
| Model/test factories | Repeated boilerplate config dicts | Consolidated defaults in `tests/factories.py` | DRY tests; consistent timezone-aware datetime usage |

# Tasks: AlphaForge Mind Initial Tabs (Feature 006)

**Input**: Design documents from `/specs/006-begin-work-on/`
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/, quickstart.md, test-matrix.md
**Architecture**: Dual Project (Brain producer, Mind consumer)

## Execution Flow (main)
(Generated per tasks template; tests precede implementation; parallelizable tasks marked [P]).

## Conventions
- (mind) paths under `alphaforge-mind/`
- (brain) only touched for new/augmented API endpoints or schemas if required (ADD only; no breaking changes)
- Contract tests validate JSON against `specs/006-begin-work-on/contracts/*.schema.json`
- FR references inline; Constitution principle abbreviations: DET (Determinism), TF (Test-First), MOD (Modularity), OBS (Observability), PERF (Performance)

## Phase 3.1: Setup
- [x] T001 Ensure dual root structure present; add README stub for `alphaforge-mind/` (mind) (FR-001..022 context) (MOD)
- [x] T002 Initialize Node deps (install) & add missing dev deps: `@types/react`, `@types/react-dom`, `@testing-library/react`, `@testing-library/jest-dom`, `@types/node`, `eslint`, plugins (mind) (TF)
- [x] T003 Create ESLint config `.eslintrc.cjs` + Prettier config + add npm scripts (mind) (MOD)
- [x] T004 Add `vitest.config.ts` with jsdom + setup file registration (mind) (TF)
- [x] T005 Add `.env.example` with `VITE_API_BASE_URL` + README section update (mind) (DOC)

## Phase 3.2: Tests First (TDD) — MUST finish before implementation
### Contract Tests
- [x] T006 [P] Contract test: candles payload -> validate `chart-candles.v1.schema.json` (tests/contracts/candles.contract.test.ts) (FR-001, FR-016) (DET, TF)
- [x] T007 [P] Contract test: backtest run request build vs `backtest-run-request.v1.schema.json` (tests/contracts/backtest-run-request.contract.test.ts) (FR-003, FR-005) (DET, TF)
- [x] T008 [P] Contract test: backtest result payload vs `backtest-result.v1.schema.json` (tests/contracts/backtest-result.contract.test.ts) (FR-007..FR-010) (DET, TF)
- [x] T009 [P] Contract test: montecarlo paths vs `montecarlo-paths.v1.schema.json` (tests/contracts/montecarlo.contract.test.ts) (FR-009, FR-017, FR-022) (DET, TF)
- [x] T010 [P] Contract test: alpha2 extended run request & montecarlo extended percentiles (schema v1alpha2) (tests/contracts/extended-alpha.contract.test.ts) (EXT-PCT, EXT-VAL future) (DET, TF)

### Unit / Store / Validation Tests
- [x] T011 [P] Unit test: date span validator (warn >5y) (tests/unit/validation/dateSpan.test.ts) (FR-021) (TF)
- [x] T012 [P] Unit test: strategy param coercion + bounds (tests/unit/strategy/params.test.ts) (FR-003, FR-013) (DET, TF)
- [x] T013 [P] Unit test: risk config validation (tests/unit/risk/riskValidation.test.ts) (FR-014) (DET, TF)
- [x] T014 [P] Unit test: run id mapping & selection logic (tests/unit/backtest/runSelection.test.ts) (FR-010, FR-019) (DET, TF)
- [x] T015 [P] Unit test: Monte Carlo default path count + percentile toggle logic (tests/unit/montecarlo/defaultPaths.test.ts) (FR-009, FR-017, FR-022) (DET, TF)

### Integration / UI Tests (jsdom level; Playwright later)
- [x] T016 [P] Integration test: Chart page loads & fetch stub called with symbol + range (tests/integration/chartPage.test.tsx) (FR-001, FR-002, FR-016) (TF)
- [x] T017 [P] Integration test: Add/remove indicators persists session state (tests/integration/indicatorsPersistence.test.tsx) (FR-002, FR-011) (DET, TF)
- [x] T018 [P] Integration test: Backtest form invalid submission blocked (tests/integration/backtestValidation.test.tsx) (FR-004) (TF)
- [x] T019 [P] Integration test: Backtest run submission triggers status polling (tests/integration/backtestRunLifecycle.test.tsx) (FR-005, FR-006) (OBS, TF)
- [x] T020 [P] Integration test: After mock result, equity + metrics + history switch works (tests/integration/backtestResultsSwitch.test.tsx) (FR-007..FR-010, FR-019) (DET, TF)
- [x] T021 [P] Integration test: Monte Carlo render baseline + opacity toggle (tests/integration/montecarloRender.test.tsx) (FR-009, FR-017, FR-022) (PERF, TF)
- [x] T022 [P] Integration test: Slow response notice after 5s simulated delay (tests/integration/slowResponseNotice.test.tsx) (FR-020) (OBS, TF)
- [x] T023 [P] Integration test: Long date span confirmation modal (tests/integration/longDateSpanWarning.test.tsx) (FR-021) (TF)
- [x] T024 [P] Integration test: Export configuration JSON (tests/integration/exportConfig.test.tsx) (FR-015) (DET, TF)

### Performance / Determinism Baseline
 - [x] T025 Performance micro-test: Monte Carlo overlay (200 paths) render time measurement harness (tests/perf/montecarloOverlay.perf.test.tsx) (FR-009, FR-022, PERF)
 - [x] T026 Determinism seed echo test (ensures equity + paths stable given same mock seed) (tests/unit/determinism/seedEcho.test.ts) (DET)

## Phase 3.3: Core Implementation
### Infrastructure & Utilities
- [x] T027 Api client wrapper (mind) `alphaforge-mind/src/services/api/client.ts` (fetch JSON, error normalization) (FR-005, FR-012) (OBS)
- [x] T028 Schema validation helper using `ajv` (mind) `alphaforge-mind/src/services/api/schemaValidator.ts` (contract test integration) (DET)
- [x] T029 Zustand store slices (chartSlice, backtestSlice) (mind) `alphaforge-mind/src/state/store.ts` (FR-002, FR-010, FR-011, FR-019) (DET)

### Chart Analysis
- [x] T030 Candle data fetch hook (mind) `src/hooks/useCandles.ts` with React Query (FR-001, FR-016) (PERF)
- [x] T031 Indicator manager component skeleton (mind) `src/components/charts/IndicatorManager.tsx` (FR-002) (MOD)
- [x] T032 CandleChart wrapper (mind) `src/components/charts/CandleChart.tsx` integrating lightweight-charts (FR-001, FR-016) (PERF)
- [x] T033 Indicator overlays integration + parameter form (mind) `src/components/charts/IndicatorPanel.tsx` (FR-002) (MOD)

### Backtest Orchestration
- [x] T034 Backtest form components (strategy + risk) (mind) `src/components/backtest/BacktestForm.tsx` (FR-003, FR-013, FR-014) (DET)
- [x] T035 Validation rules & error mapping util (mind) `src/utils/validation.ts` (FR-004) (DET)
- [x] T036 Run submission + status polling hook (mind) `src/hooks/useBacktestRun.ts` (FR-005, FR-006, FR-020) (OBS)
- [x] T037 Run history component (mind) `src/components/backtest/RunHistory.tsx` (FR-010, FR-019) (DET)

### Results Visualization
- [x] T038 Equity curve component (mind) `src/components/backtest/EquityCurveChart.tsx` (FR-007) (PERF)
- [x] T039 Metrics grid (mind) `src/components/backtest/MetricsGrid.tsx` (FR-007) (MOD)
- [x] T040 Trades summary table (mind) `src/components/backtest/TradesSummaryTable.tsx` (FR-007) (MOD)
- [x] T041 Validation summary panel (mind) `src/components/backtest/ValidationSummary.tsx` (FR-008, FR-018) (MOD)
- [x] T042 Walk-forward splits mini-chart (mind) `src/components/backtest/WalkForwardSplitsChart.tsx` (FR-018) (PERF)
- [x] T043 Monte Carlo base chart (mind) `src/components/backtest/MonteCarloChart.tsx` (FR-009, FR-017, FR-022) (PERF)
- [x] T044 Monte Carlo custom overlay optimization (batch draw) (mind) `src/components/backtest/MonteCarloOverlay.tsx` (FR-009, FR-022) (PERF)
- [x] T045 Export configuration modal (mind) `src/components/backtest/ExportConfigModal.tsx` (FR-015) (DET)

### Extended / Optional Features (Alpha2 readiness)
- [x] T046 Extended percentiles detection & UI toggle (mind) `src/components/backtest/PercentileModeToggle.tsx` (EXT-PCT) (MOD)
- [x] T047 Sensitivity/regime flags UI (hidden unless enabled) (mind) `src/components/backtest/AdvancedValidationToggles.tsx` (EXT-VAL) (MOD)

### Error & Observability
- [x] T048 Unified error boundary + notification system (mind) `src/components/common/ErrorBoundary.tsx` (FR-012) (OBS)
- [x] T049 Timing instrumentation wrapper (mind) `src/services/api/timing.ts` (FR-020) (OBS)

## Phase 3.4: Integration
 - [x] T050 Contract version manifest `specs/006-begin-work-on/contracts/VERSION.md` documenting alpha2 additive changes (DET)
- [x] T051 Add feature flag mechanism (env + store) for extended percentiles & validation toggles (mind) `src/state/featureFlags.ts` (EXT-PCT, EXT-VAL) (MOD) (completed early)
- [x] T052 Accessibility pass: focus order, aria labels, color contrast tokens audit (mind) (A11Y baseline) (DOC)
- [x] T053 Lightweight performance probe dev util (mind) `src/utils/perfProbe.ts` (PERF)

## Phase 3.5: Polish
- [x] T054 [P] Additional edge unit tests (sparse data, zero trades) (tests/unit/backtest/edgeCases.test.ts) (FR-007, FR-008) (TF)
- [x] T055 Performance refinement: memoization & rAF batching adjustments (mind) (PERF)
- [x] T056 [P] Visual regression baseline (Playwright scaffolding) (mind/tests/visual/) (FR-001, FR-009) (PERF)
- [x] T057 [P] Documentation updates: quickstart augmentation + screenshots (specs/006-begin-work-on/quickstart.md) (DOC)
- [x] T058 Refactor pass: dedupe chart hook logic (mind) (MOD)
- [x] T059 Quickstart validation run (execute dev server + run tests) record results (mind) (TF)
 - [x] T112 Add poetry self-check script reporting extras availability & env summary (brain tooling) (OBS, DET)
 - [x] T113 Slow notice UI banner + configurable threshold env (mind) (FR-020) (OBS)

## Dependencies & Ordering Notes
- T001–T005 foundational; must precede all tests.
- T006–T026 (tests) must COMPLETE before any corresponding implementation T027+ (strict TDD gate).
- Within tests, all [P] tasks can run concurrently (distinct files).
- Implementation sections can run largely in parallel by grouping (Chart, Backtest, Results) but respect internal ordering: data & hooks before components.
- Monte Carlo overlay optimization (T044) depends on base chart (T043).
- Extended features (T046–T047) depend on baseline visualization + percentiles (T043, T044).
- Version manifest (T050) after schemas already present (no blocking).

## Parallel Execution Examples
```
# Phase 3.2 example batch (after T001–T005):
T006 T007 T008 T009 T010 T011 T012 T013 T014 T015 T016 T017 T018 T019 T020 T021 T022 T023 T024 T025 T026

# Core implementation parallel groups:
Group A: T027 T028 T029
Group B: T030 T031 T032 T033
Group C: T034 T035 T036 T037
Group D: T038 T039 T040 T041 T042 T043
(Then) T044 → T045 → T046 T047 → T048 T049
```

## Validation Checklist
- [x] All contracts have tests (T006–T010)
- [x] All entities have representation tasks (store + components)
- [x] Tests precede implementation (enforced by ordering)
- [x] Parallel tasks independent (distinct file paths)
- [x] Version impact documented (T050)
- [x] Determinism & performance instrumentation tasks present (T025, T026, T049, T053)

## Traceability Matrix (FR → Tasks)
| FR | Key Tasks |
|----|-----------|
| FR-001 | T006 T016 T030 T032 |
| FR-002 | T016 T017 T031 T033 T029 |
| FR-003 | T007 T034 |
| FR-004 | T018 T035 |
| FR-005 | T007 T019 T036 T027 |
| FR-006 | T019 T036 |
| FR-007 | T008 T020 T038 T039 T040 T054 |
| FR-008 | T008 T041 T054 |
| FR-009 | T009 T021 T043 T044 T025 T056 |
| FR-010 | T020 T029 T037 T014 |
| FR-011 | T017 T029 |
| FR-012 | T027 T048 |
| FR-013 | T012 T034 |
| FR-014 | T013 T034 |
| FR-015 | T024 T045 |
| FR-016 | T006 T016 T030 T032 |
| FR-017 | T009 T021 T043 |
| FR-018 | T041 T042 |
| FR-019 | T014 T020 T029 T037 |
| FR-020 | T022 T036 T049 |
| FR-021 | T011 T023 T035 |
| FR-022 | T009 T021 T025 T043 T044 |
| EXT-PCT | T010 T046 T051 |
| EXT-VAL | T010 T047 T051 |

## Notes
- No Brain code modifications presently required (assumes endpoints already or will be added separately); if needed, add tasks T0XX under (brain) prefix later.
- Extended features are behind flags; baseline FR acceptance does not require them.

SUCCESS: Tasks ready for execution.

## Phase 3.5C: Backend Service Coverage Augmentation (Added Post Uplift)

- [x] T107 Execution rounding behavior tests (brain) Cover `services.execution.generate_trades` across FLOOR/ROUND/CEIL including sell path, zero-delta, and sub-lot suppression.
- [x] T108 Equity aggregation tests (brain) `services.equity.build_equity` ordering, peak/drawdown consistency, trade_count increments.
- [x] T109 Cold storage happy-path tests (brain) Added offload/restore round-trip, idempotent empty offload, missing manifest restore path.
- [x] T110 Retention performance optimization Add `@pytest.mark.slow` + `AF_FAST_TESTS` fast-path to heavy retention tests reducing iteration count under fast mode.
- [x] T111 Deprecate async orchestrator Quarantined `domain/run/async_orchestrator.py` (documentation stub only, `__all__` emptied) pending removal.

### Rationale
Targeted service-level tests increase confidence in execution sizing, equity state derivation, and cold storage resilience while trimming CI runtime for retention scenarios. Deprecated async orchestrator isolated to prevent accidental use.

### Follow-Up (Optional)
- Consider full removal of deprecated async orchestrator after two release cycles.
- Add compression variant parameterization to cold storage once multiple formats supported.
- Extend execution tests to include mixed sequence of increment/decrement transitions for cumulative floating rounding drift detection.

## Phase 3.3B: Brain (Backend) Additive Tasks
Backend tasks ensure contracts are actually served; all are additive (no breaking changes). Follow TDD. Sub-phases:
3.3B.1 Tests, 3.3B.2 Implementation, 3.3B.3 Integration & Docs.

### Assumptions
- Brain implemented in Python (FastAPI) per prior repo patterns (adjust if different).
- Existing base endpoints may exist; where uncertain create new versioned paths `/api/v1/...` with explicit schemas.
- Use pydantic models sourced/validated against same JSON Schemas (generate via internal tooling if available).

### 3.3B.1 Backend Test-First Tasks
- [x] T060 API schema parity tests (brain) Ensure pydantic models serialize to match `chart-candles.v1.schema.json` (DET, TF)
- [x] T061 Backtest run request validation test (brain) Reject invalid strategy params & risk config (FR-003, FR-004, FR-013, FR-014) (DET, TF)
- [x] T062 Backtest result payload shape test incl. metrics & trades aggregates (brain) (FR-007, FR-008) (DET, TF)
- [x] T063 Monte Carlo paths generation determinism test (seeded) (brain) (FR-009, FR-022) (DET, TF)
- [x] T064 Walk-forward splits computation test (brain) (FR-018) (DET, TF)
- [x] T065 Extended percentiles alpha2 test (brain) Ensure optional `p5,p95` (or configured list) present when flag passed (EXT-PCT) (DET, TF)
- [x] T066 Advanced validation toggles acceptance test (brain) Accept & echo toggles even if not yet deeply processed (EXT-VAL) (MOD, TF)

### 3.3B.2 Backend Implementation Tasks
- [x] T067 Candle data endpoint implement `/api/v1/market/candles` (brain) Pagination/time-range & symbol normalization (FR-001, FR-016) (PERF, OBS)
- [x] T068 Backtest submission endpoint `/api/v1/backtests` (POST) returns run id; validate strategy & risk (brain) (FR-003, FR-005, FR-013, FR-014) (DET, OBS)
- [x] T069 Backtest status/result endpoint `/api/v1/backtests/{run_id}` (GET) merges equity, metrics, trades summary (brain) (FR-006, FR-007, FR-008) (OBS)
- [x] T070 Monte Carlo generation sub-endpoint `/api/v1/backtests/{run_id}/montecarlo` (brain) (FR-009, FR-017, FR-022) (PERF, DET)
- [x] T071 Run history listing `/api/v1/backtests?symbol=...` (brain) (FR-010, FR-019) (MOD)
- [x] T072 Walk-forward splits endpoint (could piggyback on result or separate `/walkforward`) (brain) (FR-018) (MOD)
- [x] T073 Export config endpoint `/api/v1/backtests/{run_id}/config` (brain) returns original request canonicalized (FR-015) (DET)
- [x] T074 Extended percentiles handling (brain) Add query/body param `extended_percentiles=true` to Monte Carlo endpoint (EXT-PCT) (MOD)
- [x] T075 Advanced validation toggles passthrough & placeholder processing (brain) (EXT-VAL) (MOD)
- [x] T076 Observability: timing + structured logging correlation id middleware (brain) (FR-020, FR-012) (OBS)
- [x] T077 Rate limiting / guardrails (brain) Basic burst limit for Monte Carlo heavy calls (PERF, OBS)
- [x] T078 Deterministic seeding mechanism per run (brain) store seed with run record (FR-022, DET)

### 3.3B.3 Backend Integration & Docs
- [x] T079 OpenAPI regeneration & diff review vs `openapi.deref.json` (brain) (DET)
- [x] T080 Update backend README / CHANGELOG section for new endpoints (brain) (DOC)
- [x] T081 Add contract conformance CI job (brain) validates live responses against schemas (DET, OBS)

### Backend Dependencies Notes
- Tests T060–T066 precede implementations T067+.
- T074 depends on T070.
- T075 depends on T068 (request parsing path).
- T078 depends on T068 (seed persisted at submission) and influences T063 determinism test.
- T081 after T067–T073 minimal endpoints exist.

## Backend Traceability Addendum (FR → Brain Tasks)
| FR | Brain Tasks |
|----|------------|
| FR-001 | T067 |
| FR-003 | T061 T068 |
| FR-004 | T061 T068 |
| FR-005 | T068 |
| FR-006 | T069 |
| FR-007 | T062 T069 |
| FR-008 | T062 T069 |
| FR-009 | T063 T070 T074 T078 |
| FR-010 | T071 |
| FR-012 | T076 |
| FR-013 | T061 T068 |
| FR-014 | T061 T068 |
| FR-015 | T073 |
| FR-016 | T067 |
| FR-017 | T070 |
| FR-018 | T064 T072 |
| FR-019 | T071 |
| FR-020 | T076 |
| FR-021 | (handled client-side only) |
| FR-022 | T063 T070 T074 T078 |
| EXT-PCT | T065 T074 |
| EXT-VAL | T066 T075 |

## Additional Traceability (New Tasks)
| Requirement / NFR | Tasks |
|-------------------|-------|
| FR-001 Edge Case (sparse) | T099 |
| FR-003 Single ticker enforce | T083 |
| FR-009 Progressive reveal | T100 |
| FR-012 Error taxonomy & correlation | T094 T095 |
| FR-015 Export determinism | T096 T114 T115 T116 |
| FR-018 Splits metrics | T101 |
| FR-019 Determinism multi-run | T087 |
| FR-020 Slow notice single emission | T089 |
| FR-022 Paths bounds validation | T085 |
| EXT-PCT Flag off behavior | T097 |
| EXT-VAL Flag off behavior | T098 |
| A11Y | T092 T093 |
| Performance memory | T090 |
| Performance redraw | T091 |
| Observability correlation | T095 |
| Rate limiting | T086 T077 |
| Provenance (PROV) canonical attestation | T114 T115 T116 T117 T118 T119 T120 T121 T122 T123 |

## Validation Checklist (Updated)
- [x] All contracts have tests (T006–T010, T060–T066 for backend parity)
- [x] Backend endpoints implemented additively (no breaking changes) (T067–T073)
- [x] Determinism (T026, T063, T078) affirmed
- [x] Extended features gated (T046, T047, T074, T075, T051)
- [x] Observability in place (T027, T036, T049, T076, T081)
- [x] Performance probes/limits (T025, T043, T044, T053, T077)

## Phase 3.5B: Additional Test & Benchmark Tasks (Remediation)
Addressing /analyze CRITICAL & HIGH findings.

### Negative & Error Path Tests (Backend)
 - [x] T082 Backtest submission invalid params (missing dates, bad strategy param) → 400 (brain) (FR-003, FR-004, FR-013, FR-014) (DET, TF)
 - [x] T083 Backtest submission multi-ticker attempt → 400 single ticker enforcement (brain) (FR-003) (DET, TF)
 - [x] T084 Candles endpoint invalid interval / symbol normalization failure → 400 (brain) (FR-001) (DET, TF)
 - [x] T085 Monte Carlo request invalid paths (<20 or >500) → 400 (brain) (FR-022) (DET, TF)
 - [x] T086 Rate limiting test burst > limit on Monte Carlo → 429 (brain) (PERF, OBS)

### Determinism & Replay
- [x] T087 Duplicate backtest same seed & config returns identical metrics hash (brain) (FR-019, FR-022) (DET) — covered by `tests/integration/test_determinism_replay.py::test_two_runs_identical_outputs`
- [x] T088 Monte Carlo same seed reproducibility hash compare (brain) (FR-009, FR-022) (DET) — covered by `tests/integration/test_monte_carlo_repro.py`
	- Added metrics proxy hash assertion (fills-derived) and Monte Carlo RNG prefix stability test to harden determinism guarantees (see updated integration tests).
		- Extended with formal `metrics_hash` & `equity_curve_hash` utilities plus Monte Carlo snapshot hash test for seed+param stability.
		- NEW: Hashes now persisted into manifest.json (`metrics_hash`, `equity_curve_hash`) and exposed via RunDetail API for external verification (see `test_run_detail_hashes.py`). NumPy version guard added (`test_version_guard.py`) to fail fast on drift impacting reproducibility.
		- NEW2: Added lightweight `/runs/{hash}/hashes` endpoint returning only `manifest_hash`, `metrics_hash`, `equity_curve_hash`, and a combined `provenance_hash` (canonical hash over present components) for single-field attestation (`test_run_hashes_endpoint.py`).

### Latency & Threshold Logic
 - [x] T089 Simulated delayed result triggers single slow notice (mind) (FR-020) (OBS, TF)

### Memory & Performance Benchmarks
 - [x] T090 Memory usage capture (200 MC paths + equity) <75MB (mind) (PERF)
 - [x] T091 Monte Carlo total redraw (200 paths) <300ms median (mind) (PERF)

### Accessibility & A11Y Tests
- [x] T092 Axe scan on BacktestValidationPage no critical violations (mind) (A11Y)
- [x] T093 Keyboard navigation test (tab order through strategy form) (mind) (A11Y)

### Error Taxonomy & Observability
- [x] T094 Error taxonomy doc & test mapping backend error codes → UI messages (repo/docs + tests) (FR-012) (OBS, DET)
- [x] T095 Correlation ID propagation test (Mind sends header, Brain logs & echoes) (FR-012, Observability) (OBS)

### Export & Config Determinism
- [x] T096 Exported config JSON ordering & completeness test (mind) (FR-015) (DET)

### Feature Flags & Disabled States
- [x] T097 Extended percentiles flag off → response lacks extended_percentiles (brain) (EXT-PCT) (DET)
- [x] T098 Advanced validation toggles flag off → request fields ignored (brain) (EXT-VAL) (DET)

### Sparse / Edge Data Rendering
- [x] T099 Sparse OHLCV (gaps) chart renders placeholders (mind) (FR-001 Edge Case) (DET)

### Animation / Progressive Reveal
- [x] T100 Progressive Monte Carlo reveal test (batch load or staged rendering) (mind) (FR-009) (PERF)

### Walk-Forward Splits Metrics
- [x] T101 Walk-forward splits include metrics fields presence (brain) (FR-018) (DET)

### Backend Follow-up (New)
 - [x] T102 Dataset registration fixture for supported symbols (register NVDA/AAPL 1d) removing fallback in /backtest/run (brain) (DET, PERF)
 - [x] T103 Contract JSON schemas for backtest run request/response + contract test (align T007; add `backtest-run-create.v1.schema.json`) (DET, TF)
 - [x] T104 Status/result subset adapter endpoint `/backtests/{id}` minimal (run_id, status, created_at) for Mind polling (brain) (FR-006) (OBS, DET)
 - [x] T105 Refactor validators in `backtest_run` endpoint to Pydantic v2 `@field_validator` (remove warnings) (MOD)
 - [x] T106 Negative test unsupported timeframe (e.g. 7d) returns 400 (brain) (FR-003, FR-004) (TF)

### Mapping Existing Unmapped Tasks
- T053 (perf probe) → PERF, OBS
- T058 (refactor pass) → SIMPLICITY (Constitution IV)
- T077 (rate limiting) → PERF, OBS
- T081 (contract conformance CI) → DET, CONTRACT VERSIONING

## Updated Validation Checklist (Remediation Added)
- [x] Negative path tests pass (T082–T086) ✅ Covered by new API negative tests (invalid params, multi-ticker, bad interval/symbol, paths bounds, rate limit burst) added in Phase 3.5C.
- [x] Determinism replay tests pass (T087–T088) ✅ Duplicate run outputs & Monte Carlo seeded distributions stable.
- [x] Latency slow notice test passes (T089)
- [x] Memory & redraw benchmarks within target (T090–T091)
- [x] Accessibility baseline established (T092–T093)
- [x] Error taxonomy documented & enforced (T094)
- [x] Correlation ID propagation verified (T095)
- [x] Config export deterministic (T096)
- [x] Feature flags correct on/off behavior (T097–T098)
- [x] Sparse data rendering validated (T099)
- [x] Progressive reveal behavior validated or deferred note (T100)
- [x] Walk-forward metrics presence tested (T101)
- [x] Backtest run contract schema tests pass (T103)
- [x] Status/result adapter returns minimal payload (T104)
- [x] Deprecated validator usage removed (T105)
- [x] Unsupported timeframe validation enforced (T106)
- [x] Canonicalization endpoint returns stable ordering & hash (T114)
- [x] Frontend canonical verify flow functional (T116–T117)
- [x] Full vs light hashing equivalence (T118–T119)
- [x] Fallback hashing path covered (T120)
- [x] Canonical edge cases covered (T121)
- [x] Contract test for canonical structure (T122)
- [x] Coverage ratchet guidance documented (T123)

## Notes (Amended)
- Brain tasks inserted (T060–T081); numbering continues sequentially.
- If Brain stack differs (not FastAPI), adapt test harness accordingly but keep numbering & principles.
- Consider future pagination for `/backtests` list (T071) if result set grows.

SUCCESS: Tasks (frontend + backend) ready for execution.

## Addendum: Deterministic Hashes & New Strategy/Risk Semantics (Post Phase 3.5C)

The following additive capabilities were introduced after the initial task matrix to strengthen external verifiability (DET) and simplify baseline configuration for replay tests:

### 1. `buy_hold` Strategy
- Minimal always-invested reference strategy registered under `strategy.name = "buy_hold"`.
- Emits a constant long signal (1.0) and guarantees required equity curve columns even with sparse input.
- Used by determinism and hash-oriented integration tests as a stable, low-variance baseline.

### 2. `risk.model = "none"` Passthrough
- When risk configuration specifies a model of `none`, the sizing layer performs a no-op passthrough.
- All trade sizes remain as produced by the strategy/execution layer (typically unit size or strategy-derived) enabling focused validation of strategy + hashing without noise from position sizing algorithms.
- Tested in `tests/risk/test_risk_none_passthrough.py` ensuring zero-modification semantics.

### 3. Run Hashes & Attestation Endpoint
- New lightweight endpoint: `GET /runs/{run_hash}/hashes` returns JSON containing:
	- `manifest_hash`: Canonical hash of the persisted manifest JSON (structural ordering neutral).
	- `metrics_hash`: Hash over primary metrics payload.
	- `equity_curve_hash`: Hash over normalized equity curve sequence.
	- `provenance_hash`: Order-independent canonical combination hash of the above hashes (future-proof; additional component hashes may be concatenated canonically with stable key ordering).
- Purpose: External systems can attest a run’s integrity with a single short field while retaining component-level granularity for diffing.
- See integration coverage: `tests/integration/test_run_hashes_endpoint.py` and `tests/integration/test_run_detail_hashes.py`.

### 4. Provenance Hash Stability
- Added stability test `tests/integration/test_provenance_hash_stability.py` asserting that benign re-orderings of component hash JSON keys do not alter `provenance_hash`.
- Implementation leverages canonical serialization (`hash_canonical`) ensuring:
	- Sorted keys
	- Deterministic float formatting
	- Elimination of incidental whitespace differences

### 5. Design Notes & Future Extensibility
- Additional artifact hashes (e.g., `trades_hash`, `monte_carlo_snapshot_hash`) can be appended; provenance hash should remain stable by hashing a sorted list of `key=value` pairs or a canonical dict with enforced key ordering.
- If a component is absent (e.g., Monte Carlo not executed), it is simply omitted—stability logic excludes `None` entries rather than substituting sentinel values.
- Downstream verifiers should treat `provenance_hash` as the primary attestation token, falling back to component hashes for investigative diffing.

### 6. Operational Guidance
- Any schema or hashing algorithm change MUST increment internal version metadata and be accompanied by a failing → fixed update to the stability tests.
- For performance, the hashes endpoint avoids recomputing heavy structures; values are persisted during run finalization and loaded directly.

### 7. Rationale
- Reduces surface area for flakiness in determinism tests (DET principle reinforced).
- Enables lightweight external audit (publish only 1 field vs entire manifest) while retaining forensic depth.
- Provides a neutral, always-valid strategy/risk baseline useful for regression and environment drift detection (e.g., numeric library version changes).

No numbering retrofit into the original task matrix; this addendum documents post-matrix hardening work.

## Phase 3.5D: Canonicalization & Provenance Hardening (Added 2025-09-27)

New tasks introduced to guarantee cross-stack (Brain ↔ Mind) deterministic serialization & hashing for export / attestation flows.

### Tasks (All Completed)
- [x] T114 Canonicalization endpoint `/canonical/hash` (brain) returning `{canonical, sha256}` (DET, PROV)
- [x] T115 Frontend canonical API helper `src/services/api/canonical.ts` (mind) (DET, PROV)
- [x] T116 Export modal Verify button invoking backend canonical endpoint (mind) (FR-015, DET, PROV)
- [x] T117 Frontend verify integration test (mind) (`exportConfigModalVerify.test.tsx`) (DET)
- [x] T118 Lightweight hashing module `infra/utils/hash_light.py` (brain) side-effect minimal (PERF, DET)
- [x] T119 Equivalence tests full vs light hashing (`test_hash_light_equivalence.py`) (DET)
- [x] T120 Endpoint fallback logic (brain) prefers full hash, falls back to light on import failure (ROBUST)
- [x] T121 Expanded canonical endpoint tests (datetimes, enums, paths, nested lists, float precision) (DET)
- [x] T122 Frontend-backend canonical contract mock test (`canonicalContract.test.ts`) (DET)
- [x] T123 Coverage ratchet recommendation (commented `--cov-fail-under=30`) (QA)

### Post-Ratchet Update (2025-09-27)
Coverage floor raised from no enforced threshold to `--cov-fail-under=29` (current total ~84% after expanded backend test suite). Increment chosen to sit just below prior observed baseline (~29.7%) before recent deterministic / retention test additions. Next planned increment to 40% after stabilizing new hashing & canonicalization paths (see Next Steps priority 5). NumPy pin synchronized to environment (`2.0.2`) in `infra/version_pins.py`; upgrade to 2.1.x will require revalidation of determinism hashes and updating the guard test rationale in this document.

### Rationale
Establishes a verifiable, stable JSON + hashing pipeline enabling third parties (and the frontend) to prove equality of configuration & provenance artifacts without trusting transport ordering or incidental whitespace. The light hashing module de-risks early import cost and reduces potential circular dependency / heavy initialization side effects.

### Outcomes
- Deterministic hashes now validated across multiple structure edge cases.
- Frontend users can manually verify export payloads before external submission.
- Backend resilient to partial environment initialization (fallback hashing path).
- Clear path to ratchet coverage once foundational determinism is locked.

### New Tag
PROV = Provenance / Attestation integrity reinforcement.

---

## Appendix A: Backend Endpoint Stubs (Methods & Samples)
Stable unless versioned. Samples trimmed for clarity.

### T067 GET /api/v1/market/candles
Request (query): `?symbol=BTCUSD&interval=1h&start=2024-01-01T00:00:00Z&end=2024-01-07T00:00:00Z`
Response 200:
```
{
	"symbol": "BTCUSD",
	"interval": "1h",
	"candles": [
		{"t":"2024-01-01T00:00:00Z","o":42100.1,"h":42150.2,"l":42080.0,"c":42120.4,"v":12.345},
		{"t":"2024-01-01T01:00:00Z","o":42120.4,"h":42210.0,"l":42090.0,"c":42190.0,"v":10.112}
	]
}
```

### T068 POST /api/v1/backtests
Request Body:
```
{
	"symbol": "BTCUSD",
	"date_range": {"start":"2023-01-01","end":"2023-12-31"},
	"strategy": {"name":"ema_cross","params":{"fast":12,"slow":26}},
	"risk": {"initial_equity":10000,"position_sizing":"fixed_fraction","fraction":0.02},
	"validation": {"walk_forward": false},
	"advanced": {"regime_flags": []},
	"extended_validation_toggles": {"sensitivity": false},
	"seed": 123456789
}
```
Response 202:
```
{"run_id":"bt_01HXYZ3F9QF1KZ","status":"queued"}
```

### T069 GET /api/v1/backtests/{run_id}
Response 200 (partial):
```
{
	"run_id":"bt_01HXYZ3F9QF1KZ",
	"status":"completed",
	"equity_curve":[{"t":"2023-01-01","equity":10000},{"t":"2023-01-02","equity":10042.5}],
	"metrics":{"cagr":0.12,"max_drawdown":0.18,"sharpe":1.4},
	"trades_summary":{"count":342,"win_rate":0.54},
	"walk_forward": {"splits":[]}
}
```

### T070 POST /api/v1/backtests/{run_id}/montecarlo
Request Body:
```
{"paths":200,"seed":987654321,"extended_percentiles":false}
```
Response 200 (partial):
```
{
	"run_id":"bt_01HXYZ3F9QF1KZ",
	"paths_meta":{"count":200,"seed":987654321},
	"equity_paths":[[10000,10020,10010],[10000,10015,10030]],
	"percentiles":{"p50":[10000,10018,10022],"p90":[10000,10030,10055]}
}
```

### T071 GET /api/v1/backtests?symbol=BTCUSD&limit=20
Response 200 (partial):
```
{
	"symbol":"BTCUSD",
	"runs":[{"run_id":"bt_01H...","created":"2024-01-10T12:00:00Z","status":"completed"}]
}
```

### T072 GET /api/v1/backtests/{run_id}/walkforward (if separate)
Response 200 (partial):
```
{"run_id":"bt_01H...","splits":[{"train":{"start":"2023-01-01","end":"2023-03-31"},"test":{"start":"2023-04-01","end":"2023-05-31"}}]}
```

### T073 GET /api/v1/backtests/{run_id}/config
Response 200 (partial):
```
{"run_id":"bt_01H...","original_request":{ "symbol":"BTCUSD", "strategy": {"name":"ema_cross"}}}
```

### T074 (extended percentiles) Example Response augmentation
```
"extended_percentiles": {"p5":[...],"p95":[...]}
```

### T075 (advanced validation toggles) Example in run request
```
"extended_validation_toggles": {"sensitivity": true, "regime": true}
```

### T076 Middleware Logging Example
Correlation headers:
```
X-Request-ID: 4f5a2c9e-...
X-Processing-Time-ms: 123
```

### T078 Deterministic Seeding Storage Record
```
{"run_id":"bt_01H...","seed":123456789,"strategy_hash":"ema_cross:12:26"}
```

## Appendix B: Issue Label Suggestions
Suggested GitHub labels to streamline triage:
- `area:frontend`
- `area:backend`
- `type:test`
- `type:contract`
- `perf`
- `observability`
- `determinism`
- `feature-flag`
- `tech-debt`
- `good-first-task` (small isolated items e.g., T053, T058)
- `blocking` (if on critical path list)

## Appendix C: Risk Ranking (Top 10)
| Rank | Task(s) | Risk Vector | Mitigation |
|------|---------|-------------|------------|
| 1 | T070 T074 | Performance & memory (Monte Carlo large paths) | Cap default paths, streaming/batching, perf test (T025) |
| 2 | T068 T069 | Data correctness (metrics aggregation) | Golden fixture set + determinism seed (T026, T078) |
| 3 | T043 T044 | Frontend render perf (hundreds paths) | Canvas layering & throttle, perf probe (T053) |
| 4 | T036 | Polling & race conditions | Abort controllers, idempotent status merging |
| 5 | T028 T060 | Schema drift | Auto CI (T081), lock schema hash in tests |
| 6 | T063 T078 | Deterministic randomness | Store seed + algorithm version tag |
| 7 | T067 | Market data variability | Normalize intervals, strict time alignment tests |
| 8 | T071 | Run history growth | Add pagination & index note early |
| 9 | T076 | Observability overhead | Lazy instrumentation, sampling |
| 10 | T046 T074 | Feature flag leakage | Central flag guard + e2e check |

## Appendix D: Critical Path Extraction
Ordered minimal sequence to reach a demonstrable end-to-end backtest with Monte Carlo and chart visualization:
1. Foundations: T001–T005
2. Core contracts & backtest request/result tests: T007 T008 T009 T010
3. Determinism & seed tests: T026 T063
4. Backend submission + status: T061 T068 T069
5. Backend Monte Carlo base: T063 (verified) T070
6. Frontend API client & polling: T027 T036
7. Store + equity visualization: T029 T038
8. Monte Carlo chart + overlay: T043 T044
9. Extended percentiles (optional milestone): T074 T046
10. Observability & performance: T049 T025 T076

Mark these tasks with `blocking` label until complete.

## Appendix E: CI Additions Summary
- Added workflow `.github/workflows/contract-conformance.yml` implementing parallel backend/frontend contract checks.
- Future expansion: add caching for pip & node, add coverage upload step.

## Appendix F: Visualization Strategy Addendum (Deferred Items)
Current Decision (2025-09-27):
- Continue using `lightweight-charts` for all primary financial time-series (candles, equity, drawdown) + custom Canvas overlay (Monte Carlo) for high path counts.
- Do NOT introduce an additional general-purpose charting library (Recharts / Plotly / ECharts) during Phase 3.5; defer until a concrete need (complex heatmap / multi-dimensional sensitivity surface) is validated.
- Favor small internal primitives (`viz/`) for simple aggregates (histogram, bar, mini heatmap) using lightweight SVG/Canvas helpers to preserve bundle size and determinism.

Rationale:
- Keeps performance budget headroom and reduces variance in future visual regression baselines.
- Avoids theming fragmentation and duplicate interaction paradigms.
- Monte Carlo performance already addressed via custom canvas layer (T044, T055); further library introduction would not materially improve current scope.

Deferred Backlog Candidates (NOT scheduled; add later if justified):
- (Future) T11x Create `viz/` primitives: `TimeSeriesBase`, `HeatmapCanvas`, `Histogram`.
- (Future) T11x A11Y summary hook `useSeriesSummary` for screen-reader equity & percentile narration.
- (Future) T11x Parameter sensitivity heatmap prototype (canvas) – only after strategy parameter sweep feature defined.

Exit Criteria to Revisit Decision:
1. Requirement for interactive 2D matrix (>= 40×40 cells) with zoom/brush.
2. Need for multi-chart linked highlighting beyond what lightweight primitives can provide with modest effort.
3. Evidence of developer velocity drag from re-implementing mid-complexity chart types.

Until one trigger is met, remain on current stack to minimize cognitive & bundle overhead.

## Next Steps (Post Phase 3.5D)

| Priority | Window | Item | Tasks | Rationale | Exit Criteria |
|----------|--------|------|-------|-----------|---------------|
| 1 | Immediate | Feature flag off-path validation | T097 T098 | Close remaining deterministic config gaps behind flags | Both tests green; flags default-off semantics preserved |
| 2 | Immediate | Sparse data rendering | T099 | Ensure charts resilient to gaps (prevents rendering regressions) | Placeholder markers rendered & no JS errors on gap fixtures |
| 3 | Near | Progressive reveal optimization decision | T100 | Determine if staged rendering materially improves UX | Bench diff >15% frame time improvement or defer w/ note |
| 4 | Near | Walk-forward splits metrics presence | T101 | Completes FR-018 coverage | Metrics fields asserted across all splits in test fixture |
| 5 | Near | Raise coverage floor incrementally | (T123 follow-up) | Institutionalize quality ratchet | `--cov-fail-under` raised to 40% without flake |
| 6 | Near | Real canonical contract (live backend) | (extend T122) | Replace mock with generated sample from brain to detect drift | CI job fails on ordering/hash mismatch |
| 7 | Later | Additional artifact hashes (trades, MC snapshots) | (new T124+) | Deepen provenance scope for audit trails | New hashes emitted & provenance hash stability test passes |
| 8 | Later | Hash versioning & schema meta | (new T125) | Forward-compat for future canonical changes | Version bump triggers required test update gate |
| 9 | Later | UI signed export (client PGP/Ed25519) | (new T126) | External attest chain-of-custody | Signature appears in export & verification doc added |
| 10 | Opportunistic | Visualization primitives mini-lib | (future T11x) | Reduce duplication & enforce deterministic drawing | Shared helpers adopted by >=2 charts |

Notes:
- New tasks (T124–T126) not yet created; add when initiating provenance expansion.
- Prioritize unresolved checkboxes (T097–T101) before widening scope.
- Revisit deferred visualization library adoption only if triggers in Appendix F fire.

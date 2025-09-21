<!-- AUTO-GENERATED TASK ROADMAP (NVDA 5-Year Dataset Integration) -->
# Task Roadmap: NVDA 5-Year Historical Dataset Integration
Branch: `002-integrate-nvda-5`

Legend:
- [ ] = Not Started | [P] = Parallelizable group marker (task itself still needs completion)
- Dependency Notation: (Deps: T00X, ...)  — omit if none
- Tasks referencing DIFFERENT primary files may run in parallel (mark [P]); same file/area = sequential.

## Overview
Objective: Ingest, normalize, validate, hash, and expose a canonical 5‑year NVDA dataset with deterministic artifacts and additive OpenAPI enrichments (data_hash, calendar_id, validation summary) without breaking existing contracts.

Success Criteria:
- Deterministic `data_hash` integrated into run hashing & manifest.
- `RunDetail` and `ArtifactManifest` expose `data_hash`, `calendar_id`, `validation_summary` subset.
- `validation.json` artifact emitted with anomaly counters & events.
- All indicators, strategies, risk & execution remain stable; new tests green; additive OpenAPI diff only.

## Ordered Tasks

### Phase A – Ingestion & Normalization (Models & Core Pipeline)
 - [x] T001 Create data directory convention `data/` & document path resolution in README (Deps: —)
 - [x] T002 Implement dataset registry module (symbol -> loader metadata & cached DatasetMetadata) (Deps: T001)
 - [x] T003 Implement strict CSV loader for NVDA (`local_csv` provider): dtype coercion, timestamp parse, source TZ assumption (America/New_York) (Deps: T002)
 - [x] T004 Normalize timestamps → UTC; attach `calendar_id` (NASDAQ) & derive session date column (Deps: T003)
 - [x] T005 Enforce ascending order: sort & assert strictly increasing (Deps: T004)
 - [x] T006 Detect & drop duplicate timestamps (retain first) capturing counter & up to N samples (Deps: T005)
 - [x] T007 Drop rows with missing critical fields (o/h/l/c/volume) with counters & samples (Deps: T006)
 - [x] T008 Flag (not drop) zero-volume rows (retain w/ flag + counter) (Deps: T007)
 - [x] T009 Filter out future-dated rows (beyond current UTC now) with counter (Deps: T008)
 - [x] T010 Classify calendar gaps (expected closures vs unexpected gaps) using calendar abstraction (Deps: T009)
 - [x] T011 Compute canonical dataset hash (`data_hash`) using stable serialization (sorted columns, stable dtypes) (Deps: T010)
 - [x] T012 Persist `DatasetMetadata` (hash, counts, calendar_id, anomalies) in lightweight store (SQLite or JSON) (Deps: T011)
 - [x] T013 Implement pure slicing function (start/end) returning immutable view without mutating canonical cache (Deps: T012)

### Phase B – Validation & Artifact Emission
 - [x] T014 Build `ValidationSummary` (counters + events + gaps/closures stats) (Deps: T013)
 - [x] T015 Serialize `validation.json` artifact (deterministic ordering) (Deps: T014)
 - [x] T016 Inject `validation_summary` subset into `RunDetail` serialization (Deps: T015)
 - [x] T017 Extend `ArtifactManifest` & hashing pipeline with `data_hash`, `calendar_id` (Deps: T011, T015)
 - [x] T018 Surface anomaly metrics optionally in metrics summary (non-breaking additive) (Deps: T017)
	 - [x] T018A Test: manifest contains `data_hash` & `calendar_id`
	 - [x] T018B Test: `validation.json` structure has summary + p_values
	 - [x] T018C Test: metrics with `include_anomalies=True` returns `anomaly_counters`
	 - [x] T018D API wiring: expose anomaly counters (add test)

### Phase C – Indicators & Feature Alignment
 - [x] T019 Ensure indicator engine consumes canonical normalized frame (no duplication) (Deps: T013)
 - [x] T020 Thread zero-volume flag availability (pass-through; inert now) (Deps: T019) [P]
 - [x] T021 Enforce causal shift/no lookahead across newly ingested dataset (test adjustments) (Deps: T019)
 - [x] T022 Add unit tests verifying indicator correctness post cleaning (duplicates removed, missing dropped) (Deps: T019)

### Phase D – Strategy / Risk / Execution Integration
 - [x] T023 Validate existing `dual_sma` strategy unchanged with NVDA dataset (Deps: T022)
 - [x] T024 End-to-end integration test: dual_sma NVDA run (baseline artifact set) (Deps: T023)
 - [x] T025 Verify risk models (fixed_fraction, volatility_target, kelly_fraction) stable (Deps: T024)
 - [x] T026 Execution simulator behavior on zero-volume bars (skip/hold deterministic) (Deps: T024)
 - [x] T027 Add test: zero-volume day does not crash nor produce fill anomalies (Deps: T026) [P]

### Phase E – Metrics & Validation Extensions
 - [ ] T028 Ensure metrics unaffected by removed rows (index continuity) (Deps: T024)
 - [ ] T029 Deterministic equity curve test (repeat identical run -> identical hash & metrics) (Deps: T024)
 - [ ] T030 Integrate anomaly counters into `validation.json` fully (align names) (Deps: T015)
 - [ ] T031 Test unexpected gap detection (fixture w/ synthetic gap) (Deps: T010) [P]
 - [ ] T032 Benchmark ingestion duration (record baseline; FR-019) (Deps: T013)

### Phase F – API & Contract Adjustments
 - [ ] T033 Update `RunDetail` schema serialization (embed data_hash, calendar_id, validation_summary) (Deps: T016)
 - [ ] T034 Update `ArtifactManifest` serialization (Deps: T017)
 - [ ] T035 OpenAPI augmentation & spectral lint + version bump (Deps: T033, T034)
 - [ ] T036 Candle slice test using NVDA symbol & date bounds (Deps: T013)
 - [ ] T037 SSE event sequence test verifying anomaly summary event presence (Deps: T015) [P]

### Phase G – Idempotency & Retention
 - [ ] T038 Integrate `data_hash` into run config canonical hash pipeline (Deps: T011, T033)
 - [ ] T039 Test: modify CSV (single price change) => produces new run hash (Deps: T038)
 - [ ] T040 Confirm retention pruning logic unaffected (dataset metadata reused) (Deps: T038)

### Phase H – Tooling & Scripts
 - [ ] T041 Add PowerShell helper `scripts/run_local_nvda.ps1` producing canonical run & printing manifest path (Deps: T024)
 - [ ] T042 README augmentation linking to NVDA quickstart & deterministic notes (Deps: T041) [P]
 - [ ] T043 CI ingestion smoke test (loader only) (Deps: T003)
 - [ ] T044 Golden-run regression test (hash + key metrics snapshot) (Deps: T029)
 - [ ] T045 Integrate anomaly counts into warning budget report (optional if negligible overhead) (Deps: T018)

### Phase I – Quality Gates & Release Prep
 - [ ] T046 mypy strict pass (no new errors) (Deps: T033-T045)
 - [ ] T047 Ruff lint & format pass (Deps: T046)
 - [ ] T048 Full pytest (all new tests) (Deps: T047)
 - [ ] T049 CHANGELOG update (feature entry; propose MINOR bump 0.3.0) (Deps: T048)
 - [ ] T050 Final spec vs implementation audit; close tasks (Deps: T049)

## Parallelization Guidance Examples
- Indicators post-cleaning (T020) can run parallel with certain validation-related tests if they touch disjoint files. Example command group: `run-tasks T020 T027 T031`.
- SSE anomaly event test (T037) can run parallel with candle slice test (T036) if they operate on separate test modules.
- Documentation & helper script tasks (T041, T042) parallel once baseline integration test (T024) completes.

## Suggested Agent Execution Groups
Group 1: T001-T013 (sequential data pipeline foundation)
Group 2: [P] T014-T018 (can interleave some test scaffolding while artifacts serialize)
Group 3: [P] T019-T022 (indicator alignment & tests)
Group 4: T023-T029 (strategy & metrics core)
Group 5: [P] T030-T037 (API & additional validation tests)
Group 6: T038-T045 (idempotency + tooling + regression protections)
Group 7: T046-T050 (quality gates & release)

## File / Module Mapping (High-Level)
- Ingestion & Registry: `src/domain/data/registry.py`, `src/domain/data/ingest_nvda.py` (new)
- Calendar: `src/domain/time/calendar.py` (extend or add)
- Validation Summary: `src/domain/validation/summary.py`
- Manifest & Hash: `src/domain/run/manifest.py`, `src/domain/run/hash.py`
- API Models/Serialization: `src/api/routes/runs.py`, `src/api/schemas.py`
- Indicators/Features: `src/domain/feature/*`
- Strategy/Risk/Execution: existing `src/domain/strategy/*`, `src/domain/risk/*`, `src/domain/execution/*`
- Tests: `tests/data/`, `tests/integration/`, `tests/api/`, `tests/strategy/`
- Tooling: `scripts/run_local_nvda.ps1`, `scripts/bench/`, `scripts/reports/`

## Determinism & Integrity Hooks
- Hash includes canonical dataset bytes + config.
- Validation artifact stable ordering (sorted keys, deterministic sample slicing).
- Golden run snapshot ensures pipeline non-regression.

## Completion Gate
All T001–T050 marked done; OpenAPI diff shows additive changes only; full CI green including new smoke & regression tests.

### Phase J – Generalization (Multi-Symbol & Data Abstraction)
 - [ ] G01 Remove synthetic orchestrator candles (always use real dataset slice)
 - [ ] G02 Introduce DataSource protocol + LocalCsvDataSource implementation
 - [ ] G03 Implement dataset registry config (symbol,timeframe -> provider/path/calendar)
 - [ ] G04 Refactor ingestion to generic CSV (remove NVDA hard-coding)
 - [ ] G05 Orchestrator integration with registry/DataSource
 - [ ] G06 Multi-symbol cache isolation test
 - [ ] G07 Missing symbol/timeframe error test
 - [ ] G08 API provider stub (future external data source)
 - [ ] G09 Manifest enrichment with symbol & timeframe fields
 - [ ] G10 Run hash includes dataset snapshot binding (data_hash)

<!-- END AUTO-GENERATED -->


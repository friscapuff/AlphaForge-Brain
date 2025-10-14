---
description: "Task list for implementing Operational Guardrail Remediation"
---

# Tasks: Operational Guardrail Remediation

**Input**: Design documents from `/specs/015-addressing-pitfalls-to/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included where explicitly required by the specification (benchmark alert evidence, schema validation, waiver cadence logic, sweep acceptance).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (Setup, Foundation, US1, US2, US3, Polish)
- Paths follow the dual-root backend structure documented in plan.md

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish baseline tooling and directories used by all stories.

- [X] T001 [Setup] Add `jsonschema` dependency to `pyproject.toml` and refresh `poetry.lock` to support configuration validation.
- [X] T002 [P] [Setup] Create scaffolding directories `configs/schemas/` and `zz_artifacts/governance/` with `.gitkeep` to store schema definitions and cadence artifacts.
- [X] T003 [P] [Setup] Add fixture directories `alphaforge-brain/tests/sweeps/fixtures/` and `alphaforge-brain/tests/data/sweeps/expected/` for upcoming acceptance tests.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core governance plumbing shared across all user stories.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 [Foundation] Implement governance data classes (`ValidationPerformanceReport`, `BenchmarkTrendAlert`, `ConfigChangeLedger`, `WaiverCadenceRecord`, `SweepAcceptanceResult`) in `alphaforge-brain/src/services/governance/models.py`.
- [X] T005 [Foundation] Add persistence helpers in `alphaforge-brain/src/services/governance/storage.py` to read/write JSON artifacts under `zz_artifacts/`.
- [X] T006 [Foundation] Scaffold FastAPI router in `alphaforge-brain/src/services/governance/api.py` registering placeholder endpoints for benchmark alerts and waiver cadence snapshots.

**Checkpoint**: Governance data model and router scaffolding complete; user stories can proceed.

---

## Phase 3: User Story 1 - Restore validation runtime confidence (Priority: P1) 🎯 MVP

**Goal**: Deliver profiling evidence, automated benchmark alerts, and parquet fallback paging so runtime regressions surface immediately.

**Independent Test**: Run profiling + benchmark scripts to generate a `ValidationPerformanceReport`, trigger a synthetic regression to observe `BenchmarkTrendAlert` ticket creation, and simulate a parquet fallback to confirm Alertmanager notification.

### Tests for User Story 1

- [X] T007 [P] [US1] Add pytest coverage in `alphaforge-brain/tests/benchmarks/test_validation_profiling.py` asserting profiling output ranks at least three bottlenecks with delta percentages.
- [X] T008 [P] [US1] Add integration test `alphaforge-brain/tests/infra/test_parquet_doctor_alerts.py` verifying fallback simulation emits Prometheus metric and queued alert payload.

### Implementation for User Story 1

- [X] T009 [US1] Update `scripts/bench/profiling/run_validation_profiling.py` to generate `ValidationPerformanceReport` artifacts and capture owner assignments.
- [X] T010 [US1] Enhance `scripts/bench/compare_baseline.py` to compute deltas against `artifacts/perf_baseline.json`, emit `BenchmarkTrendAlert`, and POST to governance API when delta ≥10%.
- [X] T011 [US1] Implement `createBenchmarkTrendAlert` handler in `alphaforge-brain/src/services/governance/api.py` to persist alerts via storage helpers and return HTTP 202.
- [X] T012 [P] [US1] Update `.github/workflows/benchmarks.yml` to run the benchmark harness nightly and publish trend alerts.
- [X] T013 [US1] Extend `infra/cache/doctor.py` to emit Prometheus metric `parquet_fallback_active` and log fallback context.
- [X] T014 [US1] Add Alertmanager rule `configs/prometheus/alert_rules/parquet_fallback.yaml` (plus doc update in `docs/operations/trust_gates.md`) that pages on fallback events within 5 minutes.

**Checkpoint**: Profiling report, benchmark alerts, and parquet fallback paging verified.

---

## Phase 4: User Story 2 - Lock down governance configuration drift (Priority: P2)

**Goal**: Enforce schema-validated configuration changes, signed change logs, waiver cadence automation, and dashboard visibility.

**Independent Test**: Run CI validation script against valid/invalid tolerance files, verify unsigned changes are blocked, execute waiver cadence generator to ensure escalations trigger, and confirm governance API stores snapshots.

### Tests for User Story 2

- [X] T015 [P] [US2] Create failing tests in `alphaforge-brain/tests/governance/test_validate_configs.py` covering schema mismatch and missing signature scenarios.
- [X] T016 [P] [US2] Add pytest suite `alphaforge-brain/tests/governance/test_waiver_cadence.py` verifying age-based escalation logic.
- [X] T017 [P] [US2] Extend `alphaforge-brain/tests/governance/test_governance_api.py` to cover benchmark alert and waiver cadence endpoints.

### Implementation for User Story 2

- [X] T018 [US2] Define JSON Schema files `configs/schemas/trust_tolerances.schema.json` and `configs/schemas/retention_policy.schema.json` encoding required fields and limits.
- [X] T019 [US2] Implement `scripts/ci/validate_configs.py` using `jsonschema` to validate configs and enforce signed change-log entries.
- [X] T020 [US2] Implement `scripts/ci/waiver_cadence.py` to parse `WAIVERS.md`, compute `WaiverCadenceRecord` statuses, and emit `zz_artifacts/governance/waiver_cadence.json`.
- [X] T021 [US2] Flesh out `updateWaiverCadence` handler in `alphaforge-brain/src/services/governance/api.py` to persist cadence snapshots.
- [X] T022 [US2] Update `.github/workflows/governance.yml` to run validation and cadence scripts, uploading artifacts for dashboard ingestion.
- [X] T023 [P] [US2] Extend `scripts/ci/publish_dashboard_metrics.py` (or create if absent) to ingest cadence JSON and push metrics to dashboards.

**Checkpoint**: Config changes are schema-validated, waiver cadence automation operational, dashboards receive structured data.

---

## Phase 5: User Story 3 - Safeguard deterministic sweep execution (Priority: P3)

**Goal**: Provide deterministic sweep acceptance coverage, ensure partial-cap anomalies are reproducible, and document FR/SC mapping in runbooks.

**Independent Test**: Execute sweep acceptance pytest suite using new fixtures to reproduce partial-cap/anomaly cases, inspect generated manifests for deterministic ordering, and verify runbook entries link mitigations to FR/SC IDs.

### Tests for User Story 3

- [X] T024 [P] [US3] Author acceptance tests in `alphaforge-brain/tests/sweeps/test_acceptance.py` covering partial-cap hit, anomaly flag, and deterministic ordering outputs. (Validated via `poetry run pytest alphaforge-brain/tests/sweeps/test_acceptance.py`.)

### Implementation for User Story 3

- [X] T025 [US3] Populate fixture payloads under `alphaforge-brain/tests/sweeps/fixtures/` and expected manifests under `alphaforge-brain/tests/data/sweeps/expected/`. (Fixtures consumed by acceptance suite.)
- [X] T026 [US3] Implement sweep acceptance executor in `alphaforge-brain/src/services/orchestration/sweep_acceptance.py` to run fixtures and generate `SweepAcceptanceResult` artifacts. (Covered by acceptance suite end-to-end scenario.)
- [X] T027 [US3] Update runbooks `docs/operations/validation_backfill.md` and `docs/operations/trust_gates.md` with mitigation mapping to FR/SC IDs and acceptance suite usage notes. (Docs reflect FR-006 / SC-006 linkage and suite commands.)

**Checkpoint**: Sweep acceptance suite passes with documented deterministic outcomes.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Finalize documentation, artifacts, and release notes.

- [X] T028 [Polish] Sync `quickstart.md` steps by dry-running new scripts and adjusting commands as needed. (Verified commands for perf harness, profiling report, cache doctor, and baseline diff.)
- [X] T029 [Polish] Generate sample artifacts (`zz_artifacts/profiling/latest.json`, `zz_artifacts/governance/waiver_cadence.json`) and attach to governance evidence directory. (Artifacts regenerated 2025-10-14 UTC.)
- [X] T030 [Polish] Update `CHANGELOG.md` with summary of operational guardrail remediation work and cite relevant FR IDs. (Phase 6 polish entry added under 0.3.3-dev.)

---

## Dependencies & Execution Order

### Phase Dependencies
- **Phase 1 (Setup)** → prerequisite for all later phases.
- **Phase 2 (Foundational)** → depends on Phase 1; blocks all user stories.
- **Phase 3 (US1)** → starts after Phase 2; delivers MVP.
- **Phase 4 (US2)** → starts after Phase 2; can run parallel with Phase 3 once foundation is ready.
- **Phase 5 (US3)** → starts after Phase 2; can run parallel with prior stories but references fixtures created in Phase 1.
- **Phase 6 (Polish)** → final wrap-up after desired user stories complete.

### User Story Dependencies
- **US1**: No dependencies on other stories; must complete before declaring MVP.
- **US2**: Independent of US1 deliverables, but shares governance API; coordinate merging if working concurrently.
- **US3**: Independent of US1/US2 but consumes shared governance models/storage from foundation.

### Within-Story Ordering
- Tests (where defined) precede implementation to ensure TDD alignment.
- Shared files (e.g., `alphaforge-brain/src/services/governance/api.py`) receive sequential tasks to avoid collisions.
- Parallel tasks [P] touch distinct files/directories and can be split among developers.

---

## Parallel Examples

- **US1**: Run T007 (profiling test) and T008 (parquet fallback test) in parallel; similarly T012 (workflow update) can run alongside T013 (doctor instrumentation) once T011 is complete.
- **US2**: T015, T016, and T017 create separate test suites and can proceed concurrently before implementation tasks T018–T023.
- **US3**: T024 (tests) can start in parallel with fixture creation T025; once fixtures exist, implementation T026 can proceed.

---

## Implementation Strategy

### MVP First (User Story 1)
1. Complete Phases 1 & 2 (Setup + Foundation).
2. Deliver Phase 3 (US1) and verify profiling + alerting pipeline.
3. Produce governance evidence artifacts and share with stakeholders.

### Incremental Delivery
- After MVP, deliver Phase 4 (US2) to harden governance controls.
- Finally, deliver Phase 5 (US3) to cover sweep determinism and documentation.

### Parallel Team Strategy
- Team A: Finalize profiling and alert automation (US1).
- Team B: In parallel, implement CI validation + waiver cadence (US2) once foundation ready.
- Team C: Build sweep acceptance harness (US3), coordinating fixtures with Team A/B only for shared governance models.

---

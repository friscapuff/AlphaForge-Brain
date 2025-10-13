# Tasks: Testing Governance Hardening

**Input**: Design documents from `/specs/013-testing-governance-hardening/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md, contracts/

**Tests**: Required by FR-008 and success criteria. Each user story includes dedicated test tasks before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

**Coverage Guardrails**
- Maintain ≥90% line coverage for modules modified within each phase; capture `coverage.xml` slices under `zz_artifacts/coverage/governance/phase_<n>.xml`.
- Log Prometheus counter snapshots and audit trails for every gating flow; attach references in task PR descriptions.
- Document manual evidence (run manifests, breach logs, import guard events) in Phase 6 T040 before sign-off.
- Any task adding new surfaces must include corresponding negative tests to uphold fail-closed behavior.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish shared fixtures and sample data used across all governance stories.

- [x] T001 [Setup] Create shared governance test factory module at `alphaforge-brain/tests/fixtures/governance_factories.py` providing builders for tolerance profiles, validation aggregates, accounting ledgers, and retention records.
- [x] T002 [P] [Setup] Seed reusable manifest and retention sample payloads under `alphaforge-brain/tests/data/governance/` for downstream story tests.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core status/audit utilities required by every story.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T003 [Foundational] Introduce `RunValidationStatus` enum and helpers in `alphaforge-brain/src/models/run_validation_status.py` to centralize `PASSED`, `FAILED_VALIDATION`, and `CAUTION` semantics.
- [x] T004 [P] [Foundational] Add governance audit/metric utility in `alphaforge-brain/src/services/audit/governance_logger.py` exposing helpers to emit Prometheus counters and append audit log entries (used by trust gates, retention, import guard).

**Checkpoint**: Shared status/audit primitives ready.

---

## Phase 3: User Story 1 – Enforce causality & statistical gates (Priority: P1) 🎯 MVP

**Goal**: Automatically fail runs violating causality tolerances or Masters validation thresholds and surface the failure through metrics, manifests, and APIs.

**Independent Test**: Seed a run exceeding Sharpe or permutation thresholds; trust gate must fail closed, mark run `FAILED_VALIDATION`, emit `trust_gate_failure{gate="causality"}` and `trust_gate_config_error`, and API promotion must reject the run.

### Tests for User Story 1 (write first)

- [x] T005 [P] [US1] Author failing tolerance enforcement tests in `alphaforge-brain/tests/services/trust_gates/test_causality_tolerances.py` covering metric thresholds, manifest SLA version, and missing-config fail-closed behavior.
- [x] T005A [P] [US1] Add telemetry emission tests in `alphaforge-brain/tests/services/trust_gates/test_suite_telemetry.py` validating Prometheus counters and manifest SLA version annotations for tolerance runs.
- [x] T006 [P] [US1] Add Masters gating tests in `alphaforge-brain/tests/services/validation/test_validation_gate.py` ensuring permutation/CPCV breaches return `FAILED_VALIDATION` via `RunValidationStatus`.
- [x] T007 [P] [US1] Add API promotion conflict test in `alphaforge-brain/tests/api/routes/test_runs_promotion_failed_validation.py` asserting HTTP 409 with contract payload when validation status is `FAILED_VALIDATION`.

### Implementation for User Story 1

- [x] T008 [US1] Create versioned tolerance profile `configs/trust_gates/tolerances/causality.yaml` with Sharpe/leakage thresholds, metadata, and schema_version.
- [x] T009 [US1] Implement tolerance profile loader & validation in `alphaforge-brain/src/services/trust_gates/config_loader.py`, ensuring YAML errors raise fail-closed exceptions and emit audit entries via governance logger.
- [x] T010 [US1] Update `alphaforge-brain/src/services/trust_gates/suite_service.py` to consume the loader, enforce thresholds, and inject SLA version/config hash into `TrustGateSummary`.
- [x] T011 [US1] Extend `alphaforge-brain/src/services/trust_gates/telemetry.py` to register `trust_gate_failure` and `trust_gate_config_error` counters with tolerance profile labels.
- [x] T012 [US1] Update `alphaforge-brain/src/services/trust_gates/models.py` manifest block to persist tolerance SLA version and config hash for audit replay.
- [x] T013 [US1] Modify `alphaforge-brain/src/services/validation/pipeline.py` (and aggregator wiring) to interpret Masters significance results and return `FAILED_VALIDATION` statuses using the shared enum.
- [x] T014 [US1] Persist validation outcomes within `alphaforge-brain/src/domain/run/orchestrator.py` (and supporting models) so run lifecycle reflects the new `FAILED_VALIDATION` state.
- [x] T015 [US1] Update API layer (`alphaforge-brain/src/api/routes/runs.py`, error models, and serializers) to deny promotion of `FAILED_VALIDATION` runs per `contracts/api_validation.yaml`.
- [x] T016 [US1] Ensure retention entrypoints (`alphaforge-brain/src/domain/run/retention_policy.py`) treat `FAILED_VALIDATION` runs as non-promotable unless explicit waiver metadata is present.

**Checkpoint**: User Story 1 independently testable—gates fail closed, metrics emitted, promotion blocked.

---

## Phase 4: User Story 2 – Preserve auditable persistence & accounting evidence (Priority: P2)

**Goal**: Enforce schema-tagged persistence and accounting invariants so artifacts remain replayable and financially consistent.

**Independent Test**: Insert payload lacking `schema_version` or with accounting mismatches; persistence must reject it with schema errors, and trust gate accounting must fail with logged trade IDs.

### Tests for User Story 2 (write first)

- [x] T017 [P] [US2] Add contract test `alphaforge-brain/tests/contract/test_persistence_schema_version.py` validating API/persistence rejects records without matching `schema_version`. Confirmed passing (coverage gate excluded) via targeted pytest run.
- [x] T018 [P] [US2] Add regression tests `alphaforge-brain/tests/services/trust_gates/test_accounting_invariants.py` covering positive and negative accounting scenarios. Executed with targeted pytest (coverage gate excluded) to validate invariants.
- [x] T019 [P] [US2] Add migration validation test `alphaforge-brain/tests/scripts/test_schema_version_migration.py` ensuring deterministic upgrade scripts apply and record history. Verified with targeted pytest (coverage gate excluded).

### Implementation for User Story 2

- [x] T020 [US2] Integrate JSON Schema validation into `alphaforge-brain/src/infra/persistence.py`, attaching `schema_version` on writes and rejecting inserts/updates that fail `contracts/persistence_record.schema.json`. Loader now resolves runtime contracts directory, normalizes error messaging, and backs tests in T017.
- [x] T021 [US2] Sync persistence contract assets by copying/updating `specs/013-testing-governance-hardening/contracts/persistence_record.schema.json` into runtime `alphaforge-brain/contracts/` and wiring loader utilities. `_contracts_root` now resolves packaged runtime schemas ensuring validation passes.
- [x] T022 [US2] Publish deterministic migration script under `scripts/migrations/` to backfill schema_version and document applied script in audit logs. `backfill_schema_version.py` emits audit events with run hashes and supports CLI usage validated in T019.
- [x] T023 [US2] Implement accounting invariants module at `alphaforge-brain/src/services/trust_gates/accounting/invariants.py` emitting structured `AccountingInvariantViolation` records with offending trade IDs.
- [x] T024 [US2] Wire trust gate accounting evaluation (`alphaforge-brain/src/services/trust_gates/gates/accounting.py`) to leverage the invariants module and fail when tolerances breached.
- [x] T025 [US2] Emit Prometheus metrics and structured logs for accounting violations via governance logger.
- [x] T026 [US2] Expose `schema_version` and accounting invariant status in API responses (`alphaforge-brain/src/api/models/runs.py` and serializers) to meet contract expectations. Verified via `alphaforge-brain/tests/api/test_run_detail_new_fields.py` coverage of `persistence` and `accounting` fields.

**Checkpoint**: User Stories 1 & 2 both pass their independent tests.

---

## Phase 5: User Story 3 – Automate retention discipline & architectural separation (Priority: P3)

**Goal**: Enforce retention defaults with CLI tooling and add runtime import protection between Brain and Mind roots.

**Independent Test**: When run counts exceed policy, retention demotes unpinned runs while logging breaches; CLI pin/unpin commands persist audit logs; runtime import hook blocks `alphaforge_mind` imports outside shared utilities.

### Tests for User Story 3 (write first)

- [x] T027 [P] [US3] Add retention policy enforcement tests `alphaforge-brain/tests/domain/run/test_retention_policy_defaults.py` verifying default limits, pin preservation, and breach logging.
- [x] T028 [P] [US3] Add CLI governance tests `alphaforge-brain/tests/cli/test_retention_cli.py` covering `pin`, `unpin`, and `policy inspect` commands with audit trail assertions.
- [x] T029 [P] [US3] Add import guard tests `alphaforge-brain/tests/imports/test_cross_root_guard_runtime.py` covering both blocked Brain→Mind imports and allowed shared-utility cases.

### Implementation for User Story 3

- [x] T030 [US3] Create default retention configuration `configs/retention/policy.yaml` with version metadata, run caps, per-strategy top counts, and waiver references.
- [x] T031 [US3] Enhance `alphaforge-brain/src/domain/run/retention_policy.py` to respect new defaults, keep pinned runs beyond caps, and surface breach artefacts recorded via governance logger.
- [x] T032 [US3] Implement breach logging pipeline (`alphaforge-brain/src/services/audit/governance_logger.py` integrations) to append events to `zz_artifacts/retention_breaches.log` and Prometheus counters.
- [x] T033 [US3] Extend CLI commands in `alphaforge-brain/src/cli/retention/commands.py` to support `pin`, `unpin`, and `policy inspect`, persisting audit entries and honouring waivers.
- [x] T034 [US3] Register CLI entrypoints (`alphaforge-brain/src/cli/__init__.py` and Poetry console scripts) for the new retention subcommands.
- [x] T035 [US3] Implement runtime import hook `alphaforge-brain/src/infra/import_guard.py` and initialize it in primary entrypoints (app startup, CLI, tests) to block cross-root imports.
- [x] T036 [US3] Configure Ruff strict-plus rule (update `ruff.strictplus.toml`) or plugin to detect Brain↔Mind imports at lint time.
- [x] T037 [US3] Update governance docs (`docs/operations/trust_gates.md`, `WAIVERS.md`, Constitution quickstart anchors) to document retention defaults, waiver process, and import guard requirements, drafting any required Constitution amendments or waivers per Principle VIII and routing for steward approval.

**Checkpoint**: All three user stories independently testable; retention automation and runtime guard enforced.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final documentation, validation, and release hygiene across the feature.

- [x] T038 [Polish] Reconcile documentation updates in `README.md`, `CHANGELOG.md`, and `TYPE_HYGIENE_STATUS.md` referencing new governance behaviors and CLI usage.
- [x] T039 [Polish] Execute governance quickstart (`poetry run pytest ...`, retention sweep, import guard script) and capture results in `zz_artifacts/perf_latest.json` or run log.
- [x] T040 [Polish] Final audit: ensure contracts copied to runtime, quickstart instructions validated, and feature artifacts (`spec.md`, `plan.md`, `research.md`, `tasks.md`) cross-linked.
- [x] T041 [Polish] Benchmark trust-gate enforcement time against SC-001 (≤5s) and record metrics via governance logger/prometheus snapshot.
- [x] T042 [Polish] Measure persistence insert latency for schema validation (SC-002 ≤1s) and document results in audit artifacts.
- [x] T043 [Polish] Instrument retention sweep to capture runtime/log latency (SC-004 ≤5s per CLI action) and archive evidence.
- [x] T044 [Polish] Prepare constitution amendment proposal (if policy language updates required), route through governance steward for approval, and stage supporting docs before any constitution changes.

---

## Dependencies & Execution Order

- **Setup (Phase 1)** → none; establishes shared test data.
- **Foundational (Phase 2)** → depends on Phase 1; blocks all user stories until shared status/audit utilities exist.
- **User Story 1 (Phase 3)** → depends on Phase 2; unlocks MVP enforcement and must complete before downstream stories relying on `FAILED_VALIDATION` semantics.
- **User Story 2 (Phase 4)** → depends on Phase 2; can begin after US1 if downstream API fields rely on its results (recommended order: US1 → US2).
- **User Story 3 (Phase 5)** → depends on Phase 2 and US1 (for `FAILED_VALIDATION` status) and benefits from US2 schema logging but can start once US1 is complete.
- **Polish (Phase 6)** → execute after desired user stories are complete.

### Story Dependency Graph

`Setup → Foundational → US1 → (US2, US3 in parallel) → Polish`

### Parallel Opportunities

- After T004, different teams can tackle US1, US2, and US3 once dependencies satisfied.
- Within **US1**, tasks T005 and T006 and T007 are parallel ([P]); implementation tasks touching different files (T009–T015) can run concurrently where paths differ (e.g., T009 vs T011 vs T015).
- Within **US2**, tests T017–T019 are parallel; implementation tasks on different files (T022 migration vs T023 invariants vs T026 API) can run concurrently once shared dependencies complete.
- Within **US3**, tests T027–T029 run in parallel; runtime guard (T035/T036) can progress alongside retention CLI (T033/T034) after T030–T031 land.

## Implementation Strategy

### MVP First (Deliver User Story 1)
1. Complete Setup (T001–T002) and Foundational (T003–T004).
2. Deliver US1 (T005–T016) to enforce gating; validate via tests.
3. Optionally release or hold for further stories.

### Incremental Delivery
1. Finish phases 1–2.
2. Ship US1 → validate & release.
3. Ship US2 → validate persistence/accounting improvements.
4. Ship US3 → validate retention/import guard.
5. Apply Polish tasks for final release readiness.

### Parallel Team Strategy
- Team A: Focus on US1 implementation after foundational tasks.
- Team B: Start US2 once US1 status semantics are available.
- Team C: Start US3 runtime guard & retention tasks after US1, coordinating with Team B on shared audit logger.

---

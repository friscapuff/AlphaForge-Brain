---
description: "Task list for implementing enriched journaling artifacts, governance enforcement, and downstream contracts"
---

# Tasks: Enriching Journaling Detail, Quality, and Visualizations

**Input**: Design documents from `/specs/016-description-initiate-the/`
**Prerequisites**: `plan.md` (tech stack), `spec.md` (user stories), `research.md` (Phase 0 decisions)

**Tests**: Included where acceptance criteria demand verifiable evidence (trust gates, manifests, contracts).

**Organization**: Tasks grouped by user story to keep each slice independently shippable while respecting governance gates.

**Governance Hooks**: Retention budgets (Decision 2), trust-gate SLA ≤5 s (Decision 1), deterministic hashing reuse (Decision 4), and runtime import guard alignment are explicitly called out below.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare feature flags and scaffolding so subsequent work lands cleanly.

- [x] T001 [Shared] Add `is_enriched_journaling_enabled()` helper and inline docs to `alphaforge-brain/src/settings/flags.py` so feature toggles cleanly integrate with existing flag pattern.
- [x] T002 [P] [Shared] Create `alphaforge-brain/src/services/journaling/__init__.py` and `alphaforge-brain/src/services/journaling/artifact_paths.py` exposing `JOURNALING_ROOT = Path("zz_artifacts/journaling")` with Decision 3 burst notes.
- [x] T003 [P] [Shared] Add `zz_artifacts/journaling/.gitkeep` plus `zz_artifacts/journaling/README.md` documenting retention evidence expectations (max_runs=60, per_strategy_top=6).
- [x] T004 [Shared] Draft and publish `specs/016-description-initiate-the/data-model.md` capturing updated `CompletedTrade`, `Fill`, `TradeContextSnapshot`, and `JournalingAggregate` schemas before implementation begins.

**Checkpoint**: Journaling package skeleton, data-model documentation, and artifact root exist.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core utilities that every story depends on (hashing, retention, import guard).

- [x] T005 [Shared] Implement `alphaforge-brain/src/services/hashing/journaling_signature.py` reusing `hash_canonical` to canonicalize enriched payloads (Decision 4) and export helper via `services/hashing/__init__.py`.
- [x] T006 [Shared] Update `alphaforge-brain/src/domain/run/retention_policy.py` to classify journaling artifacts as full-run assets, logging breaches with Decision 2 metadata.
- [x] T007 [P] [Shared] Annotate `configs/retention/policy.yaml` (and add regression note in `CONFIG_CHANGELOG.md`) so journaling artifacts inherit policy_version `2025.10.13` budgets.
- [x] T008 [Shared] Extend `alphaforge-brain/src/infra/import_guard.py` + associated fixtures to whitelist `services.journaling` while asserting Mind boundary remains untouched.

**Checkpoint**: Hashing, retention, and import-guard foundations ready; user stories can proceed.

---

## Phase 3: User Story 1 – Researcher pulls enriched trade ledger (Priority: P1) 🎯 MVP

**Goal**: Emit enriched CompletedTrade/Fill artifacts with deterministic signal metadata and context snapshots.

**Independent Test**: Run a representative backtest and inspect `zz_artifacts/journaling/<run_id>/completed_trades.json` for signal metadata, MAE/MFE, and risk markers without Mind dependencies.

### Tests for User Story 1 (write before implementation)

- [x] T009 [P] [US1] Add integration test `alphaforge-brain/tests/integration/journaling/test_completed_trade_enrichment.py` covering MAE/MFE + signal metadata serialization.
- [x] T010 [P] [US1] Add unit test `alphaforge-brain/tests/unit/journaling/test_trade_context_snapshot.py` validating zero-trade fallback and deterministic hashing on snapshots.
- [x] T011 [P] [US1] Add regression test `alphaforge-brain/tests/integration/journaling/test_snapshot_reason_code.py` asserting missing market snapshots emit reason codes while keeping runs promotable per tolerance rules.

### Implementation for User Story 1

- [x] T012 [P] [US1] Extend `alphaforge-brain/src/models/fill.py` with risk markers (position classification, stop/target IDs, expectancy inputs) and docstring updates.
- [x] T013 [P] [US1] Extend `alphaforge-brain/src/models/completed_trade.py` with signal metadata, MAE/MFE, expectancy tags, and checklist status fields.
- [x] T014 [US1] Create `alphaforge-brain/src/models/trade_context_snapshot.py` (schema_versioned) capturing bid/ask, spread, volatility, checklist state.
- [x] T015 [US1] Implement `alphaforge-brain/src/services/journaling/enrichment.py` to compute derived metrics and emit snapshot-missing reason codes using Decision 4 hashing helper.
- [x] T016 [US1] Create `alphaforge-brain/src/services/journaling/writer.py` to persist per-trade payloads under `JOURNALING_ROOT/run_id/` ensuring deterministic ordering.
- [x] T017 [US1] Update `alphaforge-brain/src/services/orchestrator.py` to invoke enrichment/writer between `METRICS` and `VALIDATION`, honoring the ≤3 % runtime budget.
- [x] T018 [US1] Update `alphaforge-brain/src/services/manifest.py` and `alphaforge-brain/src/models/manifest.py` so journaling artifacts (name, schema_version, hash) appear in RunManifest outputs.

**Checkpoint**: Researchers can pull enriched trade ledger artifacts with deterministic fields.

---

## Phase 4: User Story 2 – Governance steward confirms audit readiness (Priority: P2)

**Goal**: Fail closed when journaling evidence regresses, with Prometheus + audit trails.

**Independent Test**: Deliberately remove journaling payload and run trust gate suite; it must fail, emit `trust_gate_status{gate="journaling"}`, and log governance events.

### Tests for User Story 2 (write before implementation)

- [x] T019 [US2] Add trust-gate regression test `alphaforge-brain/tests/trust_gates/test_journaling_gate.py` covering missing-field failure, waiver requirement, and metric emission.

### Implementation for User Story 2

- [x] T020 [US2] Create `alphaforge-brain/src/services/trust_gates/gates/journaling.py` to validate artifact presence, schema_version, and hash signatures via journaling_signature helper.
- [x] T021 [US2] Update `alphaforge-brain/src/services/trust_gates/suite_service.py` to register the journaling gate, enforce 5 000 ms SLA, and record latency events.
- [x] T022 [US2] Extend `alphaforge-brain/src/services/trust_gates/models.py` so TrustGate manifests include journaling diagnostics (schema_version, waiver_ref, hash).
- [x] T023 [US2] Update `configs/trust_gates/tolerances/institutional_default.yaml` with journaling requirements (mandatory fields, hash verification) and sign change-log entry.
- [x] T024 [US2] Document journaling gate behaviour and waiver policy in `docs/operations/trust_gates.md`.
- [x] T025 [US2] Enhance `alphaforge-brain/src/services/audit/governance_logger.py` to log `journaling.validation.failure` events with retention pointers.

**Checkpoint**: Trust-gate suite enforces journaling readiness with full governance telemetry.

---

## Phase 5: User Story 3 – Future frontend gets ready-made data contracts (Priority: P3)

**Goal**: Ship stable contracts + aggregates for expectancy, execution quality, and checklist compliance.

**Independent Test**: Generate journaling aggregate artifact and validate it against the published JSON schema + change log.

### Tests for User Story 3 (write before implementation)

- [x] T026 [P] [US3] Add contract validation test `alphaforge-brain/tests/contracts/test_journaling_contract.py` using jsonschema to verify aggregate + per-trade payloads.
- [x] T027 [US3] Add deterministic replay integration test `alphaforge-brain/tests/integration/journaling/test_replay_variance.py` validating aggregates stay within ±0.1% variance (SC-005).

### Implementation for User Story 3

- [x] T028 [US3] Add `alphaforge-brain/src/models/journaling_aggregate.py` defining expectancy, risk distribution, and checklist adherence metrics (with schema versions).
- [x] T029 [US3] Extend `alphaforge-brain/src/services/journaling/enrichment.py` to compute `JournalingAggregate` outputs and write `aggregates.json` alongside trade ledger.
- [x] T030 [US3] Create `alphaforge-brain/contracts/journaling_contract.schema.json` plus `alphaforge-brain/contracts/journaling_contract.example.json` mirroring emitted artifacts.
- [x] T031 [US3] Document contract usage and regeneration steps in `docs/dev/journaling_contract.md` and update `specs/016-description-initiate-the/quickstart.md` with CLI instructions.
- [x] T032 [US3] Add change-log fragment `changelog/fragments/016-journaling-contract.md` describing schema v1.0 and additive update expectations.

**Checkpoint**: Contracts and aggregates ready for downstream consumers without Brain changes.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Governance documentation, QA, and observability alignment.

- [x] T033 [Cross] Update `WAIVERS.md` and `docs/operations/validation_backfill.md` with journaling waiver cadence and evidence links.
- [x] T034 [Cross] Run `poetry run ruff check alphaforge-brain/src alphaforge-brain/tests` and address lint/import-guard warnings.
- [x] T035 [Cross] Run `poetry run pytest alphaforge-brain/tests/journaling alphaforge-brain/tests/trust_gates alphaforge-brain/tests/contracts` ensuring ≥90 % coverage retained.
- [x] T036 [Cross] Implement `alphaforge-brain/scripts/journaling/export_to_cold_storage.py` to package enriched artifacts for cold storage with completion timestamp metadata.
- [x] T037 [Cross] Add governance verification `alphaforge-brain/tests/integration/journaling/test_cold_storage_export.py` (or CLI workflow) asserting exports occur within 24 hours and append evidence to `zz_artifacts/retention_audit.log`.
- [x] T038 [Cross] Execute `poetry run python scripts/bench/perf_run.py --iterations 5 --warmup 1 --output zz_artifacts/perf_latest.json` to confirm ≤3 % runtime overhead.
- [x] T039 [Cross] Run `.specify/scripts/powershell/update-agent-context.ps1 -AgentType copilot` to register journaling artifacts for Copilot context.
- [x] T040 [Cross] Use `poetry run python alphaforge-brain/scripts/retention_cli.py sweep --evidence zz_artifacts/retention_audit.log` to show enriched artifacts obey retention policy.

**Checkpoint**: Feature ready for promotion with governance evidence and tooling updated.

---

## Dependencies & Execution Order

- **Phase 1 → Phase 2 → User Stories → Phase 6**: Setup precedes foundational work, which unblocks all user stories; polish comes last.
- **User Story Priorities**: US1 (P1) must complete before US2 and US3 to supply enriched artifacts. US2 (P2) depends on US1 outputs but can proceed in parallel with late-stage US1 hardening once artifacts exist. US3 (P3) depends on US1 data structures and can run concurrently with US2 after T012–T016.
- **Critical Dependencies**:
  - T005 must finish before any journaling hashing (T015, T020, T029).
  - T006–T008 must land before artifact writers (T016) to avoid retention/import violations.
  - T020 relies on manifest updates from T018 to inspect journaling metadata.
  - T029 relies on T015/T016 for raw inputs.

## Parallel Execution Examples

- **User Story 1**: After T012 runs, T013 can proceed in parallel with T014 because they touch different modules; once T014 lands, T015 and T016 can split between two developers (writer vs orchestrator).
- **User Story 2**: While one developer handles T020 (gate implementation), another can update tolerances/documents (T023–T024) since they operate on separate files.
- **User Story 3**: T028 (aggregate model) and T030 (schema files) can progress concurrently; integration in T029 then ties them together.

## Implementation Strategy

1. Deliver MVP by completing Phases 1–3 (up to T016) so researchers immediately gain enriched artifacts.
2. Layer governance enforcement (Phase 4) to satisfy fail-closed requirements without blocking early validation.
3. Finalize contracts (Phase 5) for downstream teams, then execute polish tasks (Phase 6) to close governance gates and performance budgets.
4. After each phase checkpoint, run targeted pytest suites to validate independent increments before moving on.

# Tasks: Trust Gate Framework

**Input**: Design artifacts in `/specs/011-trust-gate-framework/`
**Prerequisites**: plan.md · research.md · data-model.md · contracts/ · quickstart.md

## Path Conventions
- **Brain**: `alphaforge-brain/src/`, `alphaforge-brain/tests/`, `alphaforge-brain/migrations/`, `scripts/`
- **Mind**: `alphaforge-mind/src/`, `alphaforge-mind/tests/`
- **Artifacts & Docs**: `artifacts/`, `configs/`, `docs/operations/`, `WAIVERS.md`, `docs/decisions/`

## Phase 1: Setup & Baseline Foundations
- [x] T001 Create tolerance profile `configs/trust_gates/tolerances/institutional_default.yaml` capturing FR-204/FR-208 thresholds and DST handling limits.
- [x] T002 Produce canonical golden-run assets under `artifacts/trust_gates/baselines/v1/` (manifest snapshot, hash digest, signature placeholder) for determinism comparisons.
- [x] T003 Build test fixture module `alphaforge-brain/tests/fixtures/trust_gates.py` containing baseline digests, ingest snapshots, timezone samples, and ledger fixtures.
- [x] T004 Add Mind fixture payload `alphaforge-mind/tests/fixtures/trustGatePayload.ts` aligned with `contracts/api-run.trust_gate.example.json`.

## Phase 2: Tests First (TDD)
- [x] T010 [P] Add contract test `alphaforge-brain/tests/contract/test_runs_trust_gate.py` validating API payload (`api-run.trust_gate.example.json`) for FR-209/FR-210.
- [x] T011 [P] Add contract test `alphaforge-brain/tests/contract/test_trust_gate_manifest.py` verifying manifest extension schema (`manifest.trust_gate.example.json`).
- [x] T012 [P] Add contract test `alphaforge-brain/tests/contract/test_trust_gate_sse.py` covering SSE payload (`sse-trust_gate-update.example.json`).
- [x] T013 [P] Add CLI contract test `alphaforge-brain/tests/cli/test_trust_gates_entrypoint.py` asserting exit codes, subset flag handling, and artifact paths (FR-201/FR-213).
- [x] T014 [P] Add integration test `alphaforge-brain/tests/integration/trust_gates/test_golden_run_gate.py` failing until golden-run comparisons exist (FR-202).
- [x] T015 [P] Add integration test `alphaforge-brain/tests/integration/trust_gates/test_causality_gate.py` ensuring leak-catcher datasets collapse to zero performance (FR-203).
- [x] T016 [P] Add integration test `alphaforge-brain/tests/integration/trust_gates/test_ingest_idempotency_gate.py` verifying hash equality and vendor metadata persistence (FR-206).
- [x] T017 [P] Add integration test `alphaforge-brain/tests/integration/trust_gates/test_timezone_gate.py` asserting UTC normalization and DST/holiday coverage (FR-207).
- [x] T018 [P] Add integration test `alphaforge-brain/tests/integration/trust_gates/test_universe_stamp_gate.py` catching missing delisted symbols (FR-205).
- [x] T019 [P] Add integration test `alphaforge-brain/tests/integration/trust_gates/test_equity_and_accounting_gates.py` covering corporate-action reconciliation and ledger balance (FR-204/FR-208).
- [x] T020 [P] Add observability test `alphaforge-brain/tests/integration/trust_gates/test_metrics_logging.py` for structlog spans and Prometheus samples (FR-211).
- [x] T021 [P] Add governance test `alphaforge-brain/tests/integration/trust_gates/test_ci_gating.py` simulating waiver enforcement in CI (FR-210).
- [x] T022 [P] Add Mind integration test `alphaforge-mind/tests/integration/trustGateBadges.spec.ts` rendering pass/fail/waived states (FR-209/FR-210).
- [x] T023 [P] Add docs regression test `tests/docs/test_trust_gate_quickstart.py` ensuring quickstart commands stay current (FR-212).

## Phase 3: Implementation Waves

### Wave 3A · Harness & Gate Executors (Brain)
\- [x] T030 Implement CLI entrypoint `alphaforge-brain/src/cli/trust_gates.py` wiring configuration parsing and `--only` handling (FR-201/FR-213).
\- [x] T031 Implement `TrustGateSuiteService` in `alphaforge-brain/src/services/trust_gates/suite_service.py` orchestrating execution order, concurrency, and tolerance profiles (FR-201/FR-211).
\- [x] T032 Implement golden-run gate `alphaforge-brain/src/services/trust_gates/gates/golden_run.py` with diff diagnostics and baseline refresh hook (FR-202).
\- [x] T033 Implement causality gate `alphaforge-brain/src/services/trust_gates/gates/causality.py` executing leak-catcher datasets with epsilon checks (FR-203).
\- [x] T034 Implement ingest idempotency gate `alphaforge-brain/src/services/trust_gates/gates/ingest.py` including deterministic retry schedule and vendor metadata capture (FR-206).
\- [x] T035 Implement timezone gate `alphaforge-brain/src/services/trust_gates/gates/timezone.py` validating UTC alignment, DST, and leap seconds (FR-207).
\- [x] T036 Implement universe stamp gate `alphaforge-brain/src/services/trust_gates/gates/universe.py` comparing ingest outputs to canonical stamps (FR-205).
\- [x] T037 Implement equity reconciliation gate `alphaforge-brain/src/services/trust_gates/gates/equity.py` comparing adjusted/unadjusted curves (FR-204).
\- [x] T038 Implement accounting gate `alphaforge-brain/src/services/trust_gates/gates/accounting.py` reconciling ledger totals with decimal precision (FR-208).

### Wave 3B · Persistence, Contracts, Observability
- [x] T040 Create Alembic migration `alphaforge-brain/migrations/versions/xxxx_trust_gate_tables.py` adding `trust_gate_suites`, `trust_gate_results`, and manifest column (FR-209).
- [x] T041 Extend manifest writer `alphaforge-brain/src/services/manifest/manifest_writer.py` and hashing service to embed trust gate summary and signature references (FR-209).
- [x] T042 Update API & SSE (`alphaforge-brain/src/api/routes/runs.py`, `alphaforge-brain/src/events/sse_publish.py`) to serve trust gate payload (FR-209).
- [x] T043 Implement artifact writer `alphaforge-brain/src/services/trust_gates/report_writer.py` producing signed reports and diagnostics (FR-201/FR-209).
- [ ] [Future] Wire JSON artifact emission hooks in Mind once trust gate report writer outputs are finalized (depends on T043 completion).
- [x] T044 Instrument telemetry `alphaforge-brain/src/services/trust_gates/telemetry.py` adding structlog events and Prometheus metrics (FR-211).
- [x] T045 Integrate CI gating step via `scripts/ci/run_trust_gates.ps1` and update pipeline config plus `WAIVERS.md` policy hooks (FR-210).
- [x] T046 Implement Mind badge component `alphaforge-mind/src/components/TrustGateBadge.tsx` and related state management (FR-209/FR-210).
- [x] T047 Update Mind API adapter `alphaforge-mind/src/services/api/runs.ts` to surface trust gate data to UI consumers (FR-209).

## Phase 4: Performance & Documentation
- [x] T050 Extend benchmark harness `scripts/bench/perf_run.py` capturing `trust_suite.total` and per-gate spans (FR-211).
- [x] T051 Add runtime guard test `alphaforge-brain/tests/perf/test_trust_gate_runtime.py` enforcing ≤1.5× Masters baseline (FR-211).
- [x] T052 Refresh docs (`docs/operations/trust_gates.md`, `specs/011-trust-gate-framework/quickstart.md`, `README.md`) with updated workflows and tolerance tables (FR-212).
- [x] T053 Update governance artifacts (`WAIVERS.md`, `docs/governance/retention_policy.md`) outlining waiver process and metadata retention (FR-210/FR-212).

## Phase 5: Polish & Sign-off
- [x] T060 Produce security review memo `docs/security/trust_gate_metadata.md` covering baseline storage and vendor metadata handling (FR-209/FR-210).
- [x] T061 Ship Mind dashboard panel `alphaforge-mind/src/pages/Dashboard/TrustGatePanel.tsx` plus Prometheus alert wiring (FR-211).
- [x] T062 Record architecture decision `docs/decisions/011-trust-gate-framework.md` summarizing key choices and waivers (FR-209–FR-213).
- [x] T063 Compile validation evidence (test runs, benchmarks, quickstart logs) and attach to spec/plan for release checklist (FR-201–FR-213).

## Dependencies
- T002 → T014, T032.
- T003 → T014–T021, T032–T038.
- T004 → T022, T046–T047.
- T010–T023 must fail before corresponding implementation tasks T030–T047 proceed (tests-first discipline).
- T040 precedes T041–T045; T045 depends on T041 and T042.
- T043 depends on T032–T038.
- T050–T051 depend on T030–T044 being complete.
- T052–T053 follow completion of T043–T045.
- T061 depends on T046–T047 and T050–T051.

## Parallel Execution Examples
Tasks marked [P] can run in parallel when they touch different files. Example groupings:

```powershell
# Contract tests can execute together after Phase 1
task run T010
task run T011
task run T012
task run T013

# Gate integration tests can execute in parallel once fixtures exist
task run T014
task run T015
task run T016
task run T017
task run T018
task run T019

# Mind-focused workstream during Wave 3B
task run T046
task run T047
```

## Implementation Strategy
- **MVP First**: Complete Phases 1–3A to deliver a runnable trust gate harness with failing tests turning green gate-by-gate.
- **Incremental Delivery**: Merge each gate implementation after its test and diagnostics pass, then progress to persistence/observability in Wave 3B.
- **Governed Launch**: Only after Phases 3B–4 succeed should CI gating be activated; use Phase 5 to finalize security, dashboards, and audit artifacts.

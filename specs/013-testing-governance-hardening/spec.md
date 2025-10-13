# Feature Specification: Testing Governance Hardening

**Feature Branch**: `013-testing-governance-hardening`
**Created**: 2025-10-12
**Status**: Draft
**Input**: User description: "This specification defines six targeted improvements to strengthen AlphaForge’s testing and governance framework by formalizing tolerance thresholds, validation gating, schema versioning, accounting invariants, retention automation, and runtime import protection. First, Causality & Leakage Checks will evolve from passive monitoring to enforceable standards. Although a t+1 leak-catcher and causality guard exist, there are no quantitative service-level agreements (SLAs). To fix this, a new configuration file configs/trust_gates/tolerances/causality.yaml will define acceptable metrics (e.g., Sharpe ratio and equity drift) with explicit limits. The trust-gate runner will read these tolerances, fail automatically on breach, emit Prometheus metrics (trust_gate_failure{gate=\"causality\"}), and expose the SLA version in manifests for auditability. Second, Validation Orchestration Go/No-Go introduces true gating for statistical integrity. Masters’ permutation, CPCV, and ICC metrics currently compute caution flags but do not prevent promotion of invalid runs. The orchestrator and API will be extended to mark runs as FAILED_VALIDATION when statistical significance or caution thresholds are violated. These failed runs will become non-promotable under the retention policy, ensuring no overfit or invalid strategies advance without a waiver. Third, Persistence Schema Versioning improves long-term traceability. While current SQLite and JSON payloads lack explicit schema identifiers, each stored record will now include a schema_version key in both storage and API output. Corresponding JSON Schema definitions will reside in contracts/persistence/, validated before insert, and migration scripts will be published under scripts/migrations/ for compatibility management. Fourth, Equity and Accounting Invariants will formalize financial integrity checks. A new module under services/trust_gates/accounting will assert relationships such as cash + unrealized PnL + fees = equity, with explicit tolerances for rounding errors. Violations will trigger gate failures and log offending trade IDs, supported by regression tests that intentionally seed mismatches to confirm enforcement. Fifth, Retention and Pinning Defaults will codify data lifecycle governance. A configuration file configs/retention/policy.yaml will specify default limits (e.g., keep latest 50 runs, top 5 per strategy), enforced automatically by services/retention.py. A new CLI command (poetry run retention pin --run-hash ...) and documentation will accompany the change, ensuring reproducible storage discipline. Finally, Cross-Root Guard Runtime adds defense-in-depth against architectural violations. While check_cross_root.py catches Brain↔Mind imports in CI, a runtime import hook will now raise exceptions if such imports occur dynamically. A corresponding linter rule (e.g., Ruff plugin) and documentation in the Constitution will ensure the separation remains enforceable in all environments. Together, these six initiatives convert the current test suite from compliance-oriented to self-enforcing, measurable, and runtime-protected—fortifying AlphaForge’s reproducibility, causality integrity, and research credibility."

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.

  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Enforce causality & statistical gates (Priority: P1)

Research governance leads need gating that automatically fails runs when causality tolerances or validation significance thresholds are breached so no untrustworthy strategy progresses.

**Why this priority**: Without automated go/no-go enforcement, deterministic evidence can still be ignored, undermining the entire testing program.

**Independent Test**: Seed a run that violates Sharpe SLA or permutation p-value threshold and confirm the trust gate rejects it, recording a failed status without affecting other capabilities.

**Acceptance Scenarios**:

1. **Given** a trust-gate tolerance SLA file, **When** a leak-catcher run exceeds the Sharpe limit, **Then** the gate fails with `trust_gate_failure{gate="causality"}` and the run status marks failed validation.
2. **Given** a backtest whose permutation p-value exceeds the allowed threshold, **When** the orchestrator evaluates validation results, **Then** the run is marked `FAILED_VALIDATION`, excluded from promotion, and surfaced through the API.

---

### User Story 2 - Preserve auditable persistence & accounting evidence (Priority: P2)

Data stewards need schema-tagged payloads and enforced accounting invariants so historical artifacts can be replayed confidently even after format changes.

**Why this priority**: Traceability breaks when payload schemas drift silently, making audits and backfills expensive.

**Independent Test**: Insert a record with an outdated schema version or tampered accounting figures and ensure validation rejects it while other features remain unaffected.

**Acceptance Scenarios**:

1. **Given** a record missing the required `schema_version`, **When** persistence validation executes, **Then** the insert fails and the API exposes a descriptive error.
2. **Given** an equity ledger with inconsistent fees, **When** the accounting invariants module runs, **Then** the trust gate fails, logging the offending trade IDs.

---

### User Story 3 - Automate retention discipline & architectural separation (Priority: P3)

Operations teams need default retention budgets, CLI tooling, and runtime cross-root protection so storage remains controlled and architecture stays enforceable in every environment.

**Why this priority**: Manual retention processes and missing runtime guards create slow drift that eventually breaks determinism and architecture.

**Independent Test**: Configure the default policy and attempt to pin/evict runs beyond limits, then import Brain↔Mind modules dynamically to ensure defenses respond correctly without impacting other functionality.

**Acceptance Scenarios**:

1. **Given** the default retention policy file, **When** the retention service runs with more than the allowed run count, **Then** it demotes older runs while respecting pinned items and logging actions.
2. **Given** an attempt to import `alphaforge-mind` from backend runtime, **When** the import hook executes, **Then** it raises a descriptive exception and records the violation.

---

### Edge Cases

- Missing or malformed tolerance configuration MUST abort the gate, mark the run `FAILED_VALIDATION`, and emit a configuration error metric.
- How does the system handle a schema migration when historical payloads lack required fields or contain unexpected data types?
- What occurs if retention enforcement collides with manual pins that would violate storage budgets?
  - Retention sweeps that would violate storage budgets MUST skip pinned runs, log a breach, and require a waiver or policy update before eviction.
- How should the runtime import guard behave inside scripts that legitimately run in both roots (e.g., shared utilities)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Trust gate configuration MUST load tolerances from `configs/trust_gates/tolerances/causality.yaml`, fail runs when metrics exceed limits, and fail closed by aborting with `FAILED_VALIDATION` plus a `trust_gate_config_error` metric when the SLA file is missing or malformed.
- **FR-002**: Trust gate executions MUST emit Prometheus metrics including `trust_gate_failure{gate="causality"}` and record the active SLA version in run manifests.
- **FR-003**: Orchestrator and API layers MUST mark runs as `FAILED_VALIDATION` when permutation or CPCV significance thresholds are violated, preventing automatic promotion.
- **FR-004**: Retention policy logic MUST treat runs with `FAILED_VALIDATION` status as non-promotable unless an explicit waiver is registered.
- **FR-005**: Every persisted payload MUST include a `schema_version`, and inserts MUST validate against the corresponding JSON Schema in `contracts/persistence/`.
- **FR-006**: Migration scripts under `scripts/migrations/` MUST provide deterministic upgrade paths for prior schema versions and be referenced in documentation.
- **FR-007**: Accounting trust-gate module MUST assert defined invariants (cash + unrealized PnL + fees = equity) within configurable tolerances and log offending trade IDs on failure.
- **FR-008**: Regression tests MUST cover positive and negative accounting cases, ensuring mismatches trigger gate failures.
- **FR-009**: Default retention policy in `configs/retention/policy.yaml` MUST be enforced automatically, including limits for latest runs, per-strategy top runs, and manual pins.
- **FR-010**: CLI tooling MUST support pinning, unpinning, and policy inspection commands and persist audit logs for each action.
- **FR-011**: Runtime import guard MUST raise descriptive exceptions when cross-root imports occur and integrate with linting rules to surface issues during development.
- **FR-012**: Constitution and developer documentation MUST describe the new policies, tolerances, and enforcement workflows.

### Key Entities *(include if feature involves data)*

- **ToleranceProfile**: Represents the causality SLA configuration, containing metric identifiers, thresholds, version metadata, and enforcement mode.
- **ValidationGateResult**: Consolidates validation outcomes (permutation, CPCV, ICC) and exposes status values such as `PASSED`, `FAILED`, or `CAUTION`.
- **PersistenceRecord**: Abstract model for stored JSON payloads enriched with `schema_version`, validation status, and migration history.
- **AccountingInvariantViolation**: Structured record emitted when equity or fee invariants fail, including trade references and discrepancy metrics.
- **RetentionPolicy**: Defines storage budgets, pinning rules, and waiver references applied during retention sweeps.
- **ImportGuardEvent**: Captures attempted cross-root imports and records caller context for auditing.

## Coverage Matrix

| Requirement | Primary Automated Tests | Observability / Artifacts |
|-------------|-------------------------|---------------------------|
| FR-001, FR-002 | `tests/services/trust_gates/test_causality_tolerances.py`, `tests/services/trust_gates/test_suite_telemetry.py` | Prometheus counter scrape, run manifest diff in `zz_artifacts/trust_gates/` |
| FR-003, FR-004 | `tests/services/validation/test_validation_gate.py`, `tests/api/routes/test_runs_promotion_failed_validation.py` | Orchestrator audit log extract, API 409 transcript |
| FR-005, FR-006 | `tests/contract/test_persistence_schema_version.py`, `tests/scripts/test_schema_version_migration.py` | Coverage XML + migration ledger under `zz_artifacts/schema/` |
| FR-007, FR-008 | `tests/services/trust_gates/test_accounting_invariants.py` | Accounting violation sample payloads, Prometheus counter snapshot |
| FR-009, FR-010 | `tests/domain/run/test_retention_policy_defaults.py`, `tests/cli/test_retention_cli.py` | Retention sweep log, CLI audit trail entries |
| FR-011, FR-012 | `tests/imports/test_cross_root_guard_runtime.py`, `ruff` lint rule fixtures | Import guard event log, lint report attached to release packet |

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of trust-gate executions fail within 5 seconds when causality tolerances are breached, and affected runs surface `FAILED_VALIDATION` in API responses.
- **SC-002**: All persisted payloads report a matching `schema_version`, and validation rejects malformed records with documented errors in less than 1 second per insert.
- **SC-003**: Accounting invariant checks detect and log 100% of seeded mismatches during regression suites, with zero false positives in baseline runs.
- **SC-004**: Retention automation maintains storage within configured budgets across three consecutive weekly sweeps, and CLI logs pin/unpin operations within 5 seconds of execution.
- **SC-005**: Runtime import guard blocks 100% of unauthorized cross-root imports in development and production environments as measured by integration tests.

## Clarifications

### Session 2025-10-12

- Q: How should the system behave when the trust-gate tolerance configuration is missing or malformed? → A: Fail closed, mark `FAILED_VALIDATION`, emit config error metric.
- Q: How should the system handle retention conflicts when pins exceed policy limits? → A: Skip eviction, log breach, require waiver/policy change.

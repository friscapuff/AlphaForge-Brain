# Backend Quality Requirements Checklist

Purpose: Validate backend test hardening requirements before release gate
Audience: Release reviewers
Depth: Release gate
Created: 2025-10-11

## Requirement Completeness
- [X] CHK001 Are failure-mode requirements documented for all gates (determinism, contract, migrations, memory, cross-root) including expected summaries? [Completeness, Spec §FR-001, Spec §FR-002]
- [X] CHK002 Do coverage uplift requirements enumerate every targeted module (services.equity/execution/metrics, cold-storage, dataset utilities, timestamp helpers) and the ≥90% thresholds? [Completeness, Spec §FR-004, Spec §SC-002]
- [X] CHK003 Are dataset manifest generation and validation expectations fully captured (hash, schema, row count, pre-test abort behavior)? [Completeness, Spec §FR-005, Data-Model §DatasetManifest]
- [X] CHK004 Are perf gating outputs and SLA publication steps specified end-to-end (benchmark run, JSON artifact, failure propagation)? [Completeness, Spec §FR-008, Tasks §Phase 2.11]

## Requirement Clarity
- [X] CHK005 Is the structure of `quality_gates_summary.json` defined with named fields and failure semantics so diagnostics are unambiguous? [Clarity, Data-Model §QualityGateSummary, Spec §FR-001]
- [X] CHK006 Are coverage thresholds expressed numerically (line/branch/function/integration) without vague wording? [Clarity, Spec §FR-003, Spec §SC-002]
- [X] CHK007 Are dataset manifest field definitions (sha256, schema_signature, row_count) spelled out to avoid interpretation drift? [Clarity, Data-Model §DatasetManifest]
- [X] CHK008 Is the `AF_FORCE_QG_FAILURE` toggle behavior described clearly (allowed values, scope, expected gating result)? [Clarity, Plan §Summary, Tasks §Phase 0.2]

## Requirement Consistency
- [X] CHK009 Do spec, plan, and tasks reference the same skip-handling semantics for optional scripts (memory probe, etc.)? [Consistency, Spec §Edge Cases, Plan §Summary, Tasks §Phase 0.1]
- [X] CHK010 Are perf tooling fallback expectations aligned between spec edge cases and the CI integration task? [Consistency, Spec §Edge Cases, Tasks §Phase 2.11]
- [X] CHK011 Is terminology for coverage artifacts (`coverage_policy.json`) consistent across spec, plan, and tasks? [Consistency, Spec §Key Entities, Plan §Summary, Tasks §Phase 1.10]

## Acceptance Criteria Quality
- [X] CHK012 Are measurable success criteria defined for seeded gate failures (non-zero exit, recorded failure list)? [Acceptance Criteria, Spec §SC-001, Tasks §Phase 0.2]
- [X] CHK013 Can the coverage enforcement requirement be objectively verified in CI (explicit `--cov-fail-under` and module assertions)? [Acceptance Criteria, Spec §FR-003, Tasks §Phase 1.9]
- [X] CHK014 Is the perf SLA result (≤1.5× baseline, published within 5 minutes) measurable via documented artifacts? [Acceptance Criteria, Spec §SC-004, Plan §Technical Context]

## Scenario Coverage
- [X] CHK015 Are skip-state scenarios (disabled optional scripts) addressed with requirements for both detection and reporting? [Coverage, Spec §Edge Cases, Tasks §Phase 0.1]
- [X] CHK016 Are failure scenarios for missing perf tooling or dependencies specified alongside the standard happy path? [Coverage, Spec §Edge Cases, Tasks §Phase 2.11]
- [X] CHK017 Do requirements cover asset cleanup/removal flows after obsolete scaffolding is eliminated? [Coverage, Spec §FR-007, Tasks §Phase 0.3]

## Edge Case Coverage
- [X] CHK018 Are offline or missing-manifest scenarios defined with remediation guidance before tests execute? [Edge Case, Spec §Edge Cases, Tasks §Phase 0.4]
- [X] CHK019 Are memory probe edge conditions (cap breach vs. missing psutil) captured distinctly? [Edge Case, Spec §FR-006, Tasks §Phase 0.5]

## Non-Functional Requirements
- [X] CHK020 Are performance and resource constraints (RSS budgets, runtime SLA) explicitly quantified and tied to monitoring points? [Non-Functional, Spec §FR-006, Spec §SC-004, Plan §Technical Context]
- [X] CHK021 Are governance artifacts (coverage policy, perf records) required for compliance and retention? [Non-Functional, Spec §FR-008, Tasks §Phase 1.10]

## Dependencies & Assumptions
- [X] CHK022 Are external dependencies (psutil, baseline artifacts, dataset sources) cataloged with ownership and availability assumptions? [Dependency, Plan §Technical Context, Tasks §Phase 0.4, Phase 0.5]
- [X] CHK023 Are CI pipeline touchpoints and required environments (Linux runners, Windows dev parity) documented? [Dependency, Plan §Technical Context, Quickstart §1]

## Ambiguities & Conflicts
- [X] CHK024 Is the scope of pipeline asset retention (code, docs, manifests) clearly bounded so removals don’t eliminate needed artifacts? [Ambiguity, Spec §User Story 2, Tasks §Phase 0.3, Phase 1.10]
- [X] CHK025 Are responsibilities for updating governance docs (trust_gates, waivers) unambiguous across spec and tasks? [Ambiguity, Spec §Success Criteria, Tasks §Phase 2.13]

## API Contract Alignment
- [X] CHK026 Does the plan specify how OpenAPI snapshots are versioned, diffed, and published so frontend consumers stay in sync? [API Alignment, Spec §FR-009, Plan §Summary]
- [X] CHK027 Are tasks assigned to regenerate the `alphaforge-mind` client and run smoke tests when schema changes occur? [API Alignment, Tasks §Phase 1.11]
- [X] CHK028 Does the quickstart document the end-to-end workflow for backend developers to verify the contract and trigger frontend validation locally? [API Alignment, Quickstart §6]

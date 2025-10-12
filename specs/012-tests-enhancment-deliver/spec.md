# Feature Specification: Test Hardening & Coverage Elevation

**Feature Branch**: `[012-tests-enhancment-deliver]`
**Created**: 2025-10-11
**Status**: Draft
**Input**: User description: "Tests Enhancment Deliver a test-hardening initiative that deletes dead test scaffolding, removes the unused async orchestrator, and rewires run_quality_gates.py to assert on real regressions so our gates reliably fail when determinism, schema drift, or memory caps break. Elevate coverage by backfilling unit tests for services.equity, services.execution, services.metrics, cold-storage round trips, dataset checksum validation, and timestamp utilities, pushing overall line, batch, integration, and function coverage to at least 90%. Expand the quality-gate suite with deliberate failure-path tests and enforce higher --cov-fail-under thresholds to protect that coverage floor. Tighten canonical data fixtures with hash checks and schema guards so any tampering or drift immediately stops the pipeline. Finish the memory cap probe with real RSS tracking and perf job gating to prevent stealthy resource regressions. This work keeps our green builds truthful by ensuring every pass reflects deterministic data integrity and trustworthy automation."

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

### User Story 1 - Quality gates block regressions (Priority: P1)

Reliability stewards need the unified quality-gate command to fail whenever determinism replay, schema drift, or memory cap rules are violated so releases never promote with silent regressions.

**Why this priority**: Without trustworthy gates, the rest of the stream is meaningless; failing fast on real defects preserves production integrity.

**Independent Test**: Trigger the quality-gate script with seeded failure fixtures (tampered OpenAPI, forced memory overage, determinism diff) and assert the command exits non-zero with actionable diagnostics.

**Acceptance Scenarios**:

1. **Given** the determinism replay artifacts differ from baseline, **When** the quality-gate script runs, **Then** it exits non-zero and records the determinism failure in `quality_gates_summary.json`.
2. **Given** the memory probe reports RSS above the configured threshold, **When** the script runs, **Then** the memory gate marks the run as failed and surfaces the measured RSS and limit in the summary payload.

---

### User Story 2 - Coverage uplift enforces correctness (Priority: P2)

Runtime maintainers need focused unit and integration suites for the equity, execution, metrics, cold-storage, and dataset utilities so every critical branch is validated and coverage thresholds reflect reality.

**Why this priority**: Raising coverage to 90% across line, batch, integration, and function layers catches logic regressions early and defends against stale scaffolding.

**Independent Test**: Run the targeted suites with coverage collection enabled and confirm that each module reports high branch/function coverage while the global `--cov-fail-under` threshold rejects regressions.

**Acceptance Scenarios**:

1. **Given** the updated pytest configuration, **When** the CI suite runs, **Then** it enforces a `--cov-fail-under` ≥ 90 and fails if coverage drops below that floor.
2. **Given** newly added unit tests for `services.equity`, `services.execution`, and `services.metrics`, **When** a regression is introduced (e.g., incorrect aggregation math), **Then** the corresponding unit test fails with precise diagnostics.

---

### User Story 3 - Data fixtures guarantee provenance (Priority: P3)

Data engineers require canonical datasets and timestamp utilities to reject tampering so the pipeline only runs against trusted inputs.

**Why this priority**: Ensuring fixtures fail fast when data drifts protects determinism and avoids misleading performance deltas.

**Independent Test**: Replace a canonical dataset with a corrupted version and run the fixture-driven suite to confirm tests halt with hash and schema mismatch errors.

**Acceptance Scenarios**:

1. **Given** the NVDA canonical fixture detects a hash mismatch, **When** tests import the dataset, **Then** the suite raises a deterministic error that prevents downstream test execution.
2. **Given** timestamp helpers receive timezone-naive inputs, **When** the utility tests run, **Then** they fail with explicit guidance to use UTC-aware datetime values.

---

### User Story 4 - Frontend contract stays in lockstep (Priority: P2)

Frontend integrators need guaranteed synchronization between the backend OpenAPI contract and the generated frontend client so UI releases never ship against stale endpoints.

**Why this priority**: Breaking API changes cascade into frontend outages; keeping the contract diff-tested and artifacts regenerated preserves cross-team velocity.

**Independent Test**: Diff the generated OpenAPI snapshot against the published baseline, regenerate the TypeScript client used by `alphaforge-mind`, and run the smoke suite to confirm no breaking changes or missing operations.

**Acceptance Scenarios**:

1. **Given** a backend change that modifies an endpoint schema, **When** the OpenAPI snapshot diff job executes, **Then** it surfaces the breaking change and the release blocks until the frontend client is regenerated.
2. **Given** the API contract has not changed, **When** the frontend contract verification pipeline runs, **Then** it reports a clean diff and leaves the generated client untouched for deterministic builds.

---

### Edge Cases

- Quality gate fixtures must still pass when optional scripts (e.g., memory probe) are intentionally skipped; ensure summaries distinguish "skipped" from "pass" without masking failures.
- Coverage enforcement should tolerate deliberate exclusions (e.g., generated models) only when explicitly annotated, preventing accidental blanket ignores.
- Dataset checksum validation must operate offline-friendly; if manifests are missing, the suite should fail with remediation guidance rather than silently skipping.
- Perf job gating must handle environments without perf tooling by marking the run as failed with a descriptive message instead of hanging.
- OpenAPI snapshots must remain reproducible across environments so frontend client generation yields identical artifacts; mismatched tooling versions or missing contracts should fail fast with remediation hints.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST fail the unified quality-gate command whenever determinism replay, OpenAPI drift, migration head, memory cap, or cross-root checks report a violation, including actionable context in `quality_gates_summary.json`.
- **FR-002**: System MUST add negative-path tests for each gate (determinism, contract, migrations, memory, cross-root) that seed controlled failures and assert the script exits non-zero.
- **FR-003**: Pytest configuration MUST raise the global `--cov-fail-under` threshold to ≥ 90 and treat coverage drops as test failures in CI.
- **FR-004**: Targeted unit and integration suites MUST cover `services.equity`, `services.execution`, `services.metrics`, cold-storage success and error paths, dataset checksum helpers, and timestamp utilities to achieve ≥ 90% line, branch, integration, and function coverage.
- **FR-005**: Canonical dataset fixtures MUST verify file hashes, schema signatures, and row counts before tests run, aborting execution on any mismatch.
- **FR-006**: Memory cap probing MUST collect RSS metrics for relevant test runs, compare against configurable budgets, and surface failures via both exit codes and artifact logs.
- **FR-007**: Obsolete scaffolding (e.g., async orchestrator, unused test harnesses) MUST be removed to prevent dead code from masking regressions.
- **FR-008**: Perf job gating MUST trigger as part of CI, uploading the benchmark JSON and failing when trust-gate runtime exceeds the enforced SLA.
- **FR-009**: Backend MUST publish versioned OpenAPI snapshots, diff them against the baseline, regenerate the frontend client (`alphaforge-mind`) artifact on change, and block release until frontend smoke tests confirm compatibility.
- **FR-010**: Trust-gate and Masters validation suites MUST emit span-level telemetry and Prometheus-compatible metrics (`trust_gate_status{gate=...,status=...}`, `validation_suite_duration_ms`, etc.) so observability dashboards reflect pass/fail outcomes and performance regression trends in real time.

### Non-Functional Requirements

- **NFR-001**: Trust-gate runtime MUST remain ≤ 1.5× the currently published baseline (≤ 42.73 ms mean) and surface SLA breaches within 5 minutes of CI completion.
- **NFR-002**: Memory probe MUST operate deterministically across Linux and Windows runners by using psutil to capture RSS and failing runs whenever RSS exceeds configured caps.
- **NFR-003**: OpenAPI snapshot generation MUST produce byte-identical output across supported toolchains (Poetry, Node.js 18, pnpm) and contract verification MUST block release on drift.
- **NFR-004**: Quality-gate, perf, coverage, and frontend contract artifacts MUST be persisted under `zz_artifacts/` with SHA-256 hashes recorded for compliance reviews.

### Key Entities *(include if feature involves data)*

- **QualityGateSummary**: Structured record capturing gate names, exit codes, failure reasons, timestamps, and measured metrics (hashes, RSS) for audit and dashboards.
- **CoverageThresholdPolicy**: Configuration snapshot describing required coverage floors (line, branch, integration, function) and module-level exceptions with justifications.
- **DatasetManifest**: Canonical hash and schema definition for shared fixture data, storing dataset version, row counts, checksum, and last verification timestamp.
- **PerfSlaRecord**: Benchmark artifact storing trust-gate runtime measurements, baseline comparison, and gating thresholds used for pass/fail evaluation.
- **FrontendApiContractSnapshot**: Pair of artifacts capturing the canonical OpenAPI spec and generated client commit hash for `alphaforge-mind`, including diff metadata and verification status.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Quality-gate command exits non-zero with descriptive diagnostics for 100% of seeded failure scenarios across determinism, contract drift, migrations, memory, and cross-root checks.
- **SC-002**: CI coverage reports show ≥ 90% line, branch, integration, and function coverage, with automated enforcement preventing merges below the threshold.
- **SC-003**: Canonical dataset fixture validation blocks ≥ 99% of tampering attempts by failing before dependent tests execute, as measured via controlled corruption runs.
- **SC-004**: Trust-gate performance job publishes runtime artifacts on every CI run, with SLA violations surfaced within 5 minutes via failed pipelines and recorded in `PerfSlaRecord`.
- **SC-005**: Frontend contract verification pipeline reports zero breaking changes after OpenAPI snapshot regeneration, with regenerated client artifacts committed and smoke tests passing before release.

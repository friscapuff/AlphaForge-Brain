# Implementation Plan: Param Sweep Introduction

**Branch**: `014-param-sweep-introduction` | **Date**: 2025-10-13 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/014-param-sweep-introduction/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Enable deterministic parameter sweeps so each strategy parameter can be supplied as a single value, explicit list, or numeric range. Multi-ticker submissions remain optional and are processed per ticker: the backend normalizes each ticker independently, expands parameters into a stable combination set, executes one canonical run per combo, and emits sweep telemetry plus a parent manifest that preserves lineage for governance, retention, and future Mind UI consumption. Every payload flows through documented trust-gate checkpoints (payload validation → normalization → orchestrator → manifest), each capturing sanitized parameter evidence and data-quality telemetry.

## Technical Context

**Language/Version**: Python 3.11 (Poetry-managed environment)
**Primary Dependencies**: FastAPI, Pydantic, internal orchestration/validation services, pytest + ruff/mypy tooling
**Storage**: Existing SQLite manifests, artifact directories, and optional Parquet/CSV caches (no new storage engines)
**Testing**: pytest (unit, integration, contract), property tests for determinism (including sequential execution validations for multi-ticker payloads), governance benchmark harness
**Observability**: Telemetry streams emit `sweep_id`, `ticker`, `checkpoint`, `data_quality_status`, `cap_status`, and latency metrics; audit logs persist the same fields for trust-gate review, explicitly distinguishing data-quality failures from cap rejections.
**Target Platform**: Deterministic backend services running on developer workstations and CI (Linux/Windows)
**Project Type**: Dual-root monorepo (alphaforge-brain backend focus for this feature)
**Performance Goals**: Maintain trust-gate SLA (<5s) and sweep overhead ≤10% versus sequential manual runs; reject over-cap sweeps in <2s and satisfy clean-data variance ≤0.1% compared with baseline single runs, measured independently per ticker batching.
**Constraints**: Deterministic ordering, sequential execution unless governance approves queues, combination cap enforced per ticker submission (no cross-ticker cartesian products), no cross-root imports
**Dependencies**: Continues to rely on Brain's data-validation and reconciliation services to supply curated financial inputs for each ticker prior to sweep expansion.
**Scale/Scope**: Single power user initiating sweeps up to configured combo cap (guardrails initially targeting tens-to-low-hundreds combinations) with optional batching of a small set of tickers per request.

## Constitution Check

- **Principle I – Determinism First**: Sweep expansion and execution must preserve deterministic ordering; plan enforces sequential processing and stable manifests per ticker even when multiple tickers are submitted together. ✅
- **Principle II – Test-First & Traceability**: Each FR will gain dedicated unit/integration tests (validation of expansion, guardrails, manifests) before implementation. ✅
- **Principle V – Observability & Forensic Auditability**: Parent manifest and telemetry updates ensure sweep lineage and metrics are recorded. ✅
- **Principle VI – Performance Discipline**: Combination cap, measurement of sweep overhead, and updates to perf/gov artifacts keep SLAs intact, including explicit rejection latency (T021A) and telemetry arrival (T021B) checks. ✅
- **Principle VIII – Documentation as Executable Interface**: Quickstart, contracts, and runbooks will document sweep usage and governance implications. ✅
- **Principle IX – Multi-Project Architecture**: Work isolated to alphaforge-brain APIs/artifacts with contract interfaces for future Mind integration. ✅
- **Principle X – Contract Versioning**: New/updated schemas (parent manifest, API payloads) will be versioned and accompanied by migration guidance. ✅

No constitutional violations identified; proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```
specs/014-param-sweep-introduction/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
└── tasks.md  # created during /speckit.tasks
```

### Source Code (repository root)

```
alphaforge-brain/
├── src/
│   ├── api/
│   │   └── routes/
│   ├── domain/
│   ├── models/
│   ├── services/
│   │   ├── sweeps/        # new sweep orchestration utilities
│   │   └── trust_gates/
│   ├── infra/
│   └── lib/
└── tests/
    ├── api/
    ├── domain/
    ├── integration/
    ├── contract/
    └── unit/
```

**Structure Decision**: Extend existing alphaforge-brain backend structure by introducing a `services/sweeps` module (and related tests) while keeping API, models, and manifest code within current bounded contexts. The orchestrator will iterate tickers sequentially inside a request to maintain deterministic evidence, and alphaforge-mind changes remain deferred to a future feature.

## Complexity Tracking

No additional complexity exceptions required; existing architecture accommodates the feature. Table intentionally left empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|

## Governance Alignment

- **Trust-Gate Evidence**: T010A, T011A, T011B, T011C, and T016A ensure payload validation, normalization edge cases, malformed input handling, zero-combo failures, and retry flows are covered before implementation; each maps to FR-004, FR-009, and FR-010.
- **Multi-Ticker Parity**: T016B covers SC-005 by proving multi-ticker sweeps maintain parity with single-ticker baselines inside manifests and telemetry.
- **Telemetry Verification**: T019A, T021A, T021B, and T021C verify payload fields, rejection latency, telemetry arrival SLAs, and clean-data variance, providing evidence for FR-007, SC-003, SC-004, and SC-006.
- **Per-Ticker Guardrails**: T017, T018, and T021C coordinate to prove combination caps apply independently per ticker, documenting waiver expectations inside manifests when one ticker is rejected and others proceed.
- **Documentation Sync**: T001, T021, and quickstart updates capture where reviewers find sanitized manifests, per-ticker directories, and telemetry dashboards.

## Testing Remediation Roadmap

To keep the overall suite trustworthy while Param Sweep lands, execute the following supporting workstream (see tasks T025–T027):

1. **Async contract alignment** – Adjust `/runs` API tests to expect `202 Accepted`, then poll the run detail endpoint or registry before verifying dataset fields.
2. **Coverage gate right-sizing** – Replace the blanket 90% fail-under with scoped coverage targets and a diff-aware gate so legacy debt is visible but non-blocking.
3. **Validation containment** – Standardize lightweight validation fixtures for unit/integration tests and document the dedicated smoke run that exercises the full Masters pipeline.

Complete this remediation stream before declaring the feature production-ready; it removes current blockers to an honest green full-suite run.

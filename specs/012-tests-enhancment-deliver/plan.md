## Technical Context
**Language/Version**: Python 3.11 (Poetry-managed virtualenv)
**Primary Dependencies**: pytest, coverage.py, psutil (RSS capture), FastAPI/uvicorn, ruff/mypy, Node.js 18+, pnpm, openapi-typescript generator, Playwright smoke suite (`alphaforge-mind`)
**Storage**: Filesystem artifacts (`zz_artifacts/`, `artifacts/`), SQLite manifests
**Testing**: pytest (unit/integration/CI/perf), trust-gate smoke harness, perf benchmark runner, frontend API contract smoke tests (`pnpm run smoke:api`)
**Target Platform**: GitHub Actions (Linux) and developer workstations (Windows/macOS)
**Project Type**: Dual-root (brain backend + mind client tooling)
**Performance Goals**: Trust gate ≤ 42.73 ms mean (≤ 1.5× baseline), perf harness unaffected materially, OpenAPI regeneration < 30 s, memory probe enforces configured caps
**Constraints**: Deterministic execution, ≥ 90 % coverage (line/branch/function/integration), reproducible contracts, trust-gate telemetry required per constitution principle V
**Scale/Scope**: Backend governance uplift with supporting scripts/tests; frontend client only touched via generated artifacts
## Constitution Check
- Determinism & reproducibility → **PASS** (hash manifests, seeded tests, trust-gate baselines)
- Test-first discipline → **PASS** (FR-to-test mapping, new suites before behavior changes)
- Additive contracts → **PASS** (only additive OpenAPI snapshots + governance artifacts)
- Observability & automation → **PASS** (new telemetry requirement + CI integration)
- Performance guardrail → **PASS** (perf SLA + memory probe tasks)
- Post-Phase-1 review → **PASS** (research/data model/contracts align; no waivers needed)
## Project Structure
### Documentation (feature package)
```
specs/012-tests-enhancment-deliver/
├── plan.md
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
└── tasks.md
```
### Source Layout (dual root)
```
alphaforge-brain/
├── src/
│   ├── services/
│   ├── infra/
│   ├── domain/
│   └── scripts/ci/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── ci/
│   └── perf/
└── scripts/contracts/

alphaforge-mind/
├── src/
└── tests/

shared/
└── … (pure utilities as needed)

zz_artifacts/ (generated governance artifacts)
```

**Structure Decision**: Continue operating in the dual-root layout; backend implementation and tests live under `alphaforge-brain/`, with contract verification tooling in `scripts/contracts/` and documentation under the feature spec directory.

## Phases & Execution Overview

- **Phase 0 – Gate Fixtures & Cleanup**: Create failure-path fixtures, harden `run_quality_gates.py`, remove async orchestrator, add dataset manifest tooling, finish memory probe.
- **Phase 1 – Coverage & Governance**: Expand service/unit coverage, ratchet pytest thresholds, publish coverage/perf governance artifacts, wire frontend contract verification.
- **Phase 2 – Telemetry & Perf Integration**: Integrate perf gate in CI, emit trust-gate telemetry/Prometheus metrics, update waiver/documentation process, and execute final sign-off run.
# Implementation Plan: Test Hardening & Coverage Elevation

**Branch**: `[012-tests-enhancment-deliver]` | **Date**: 2025-10-11 | **Spec**: [`spec.md`](./spec.md)
**Input**: Feature specification from `/specs/012-tests-enhancment-deliver/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

We will harden AlphaForge’s quality gates, remove obsolete scaffolding, raise automated coverage enforcement, and keep the frontend contract in lockstep so every CI pass reflects deterministic data integrity the UI can trust. Round one adds failure-path fixtures for determinism replay, OpenAPI drift, migrations, memory caps, and cross-root checks, updating `run_quality_gates.py` to surface fatal errors with actionable JSON and to honor optional-script skip semantics. Subsequent phases delete the unused async orchestrator, backfill unit/integration suites for critical services and utilities to reach ≥90% coverage across line/branch/function layers, enforce coverage thresholds, validate canonical dataset manifests, complete the RSS-based memory probe, and publish governance artifacts that wire results into CI dashboards. In parallel we version the OpenAPI snapshot, regenerate the `alphaforge-mind` TypeScript client on change, diff-check API compatibility, and add release gates that require frontend smoke tests to pass whenever the backend contract moves, while ensuring perf gating gracefully reports missing-tool cases with remediation guidance.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.11 (Poetry-managed virtualenv)
**Primary Dependencies**: pytest, coverage.py, psutil (for RSS capture), FastAPI/uvicorn stack, ruff/mypy tooling, Node.js 18+, pnpm, openapi-typescript generator, Playwright smoke suite (via `alphaforge-mind`)
**Storage**: Local filesystem artifacts (`zz_artifacts/`, `artifacts/`), SQLite manifests
**Testing**: pytest test matrix (unit, integration, perf, property), quality-gate smoke harness, benchmark runner, frontend API contract smoke suite via Playwright stubs in `alphaforge-mind` (`pnpm install`, `pnpm run generate-client`, `pnpm run smoke:api`)
**Target Platform**: CI on Linux (GitHub Actions) and developer workstations (Windows/macOS)
**Project Type**: Backend (alphaforge-brain) with supporting scripts; contracts consumed by `alphaforge-mind` frontend client
**Performance Goals**: Trust gate runtime ≤ 1.5× baseline (≤ 42.73 ms mean), memory probe enforces configured RSS budgets, test wall-clock unaffected materially, OpenAPI regeneration stays <30s to avoid slowing frontend pipelines
**Constraints**: Deterministic execution, ≥90% line/branch/function/integration coverage, artifacts hashed/validated before use, contract diffs must be reproducible across Linux/Windows toolchains with pinned Node.js/pnpm versions documented in tooling guidelines
**Scale/Scope**: Single-user research lab backend with hundreds of tests; scope limited to quality gates, testing utilities, and governance artifacts

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Determinism & reproducibility: Plan reinforces deterministic fixtures (hash manifests, seeded tests) and expands failure-path checks → **PASS**
- Test-first discipline: Adds unit/integration coverage prior to behavior changes, negative-path tests for gates → **PASS**
- Additive contracts: No breaking API changes planned; internal JSON schema additions documented → **PASS**
- Observability & automation: Extends diagnostics, coverage enforcement, perf gating in CI → **PASS**
- Performance guardrail: Memory probe + trust-gate SLA maintained → **PASS**
- Post-Phase-1 review: Design artifacts (research/data model/contracts) align with constitution principles; no new violations introduced → **PASS**

## Project Structure

### Documentation (this feature)

```
specs/012-tests-enhancment-deliver/
├── plan.md              # This file (/speckit.plan output)
├── spec.md              # Approved feature spec
├── research.md          # Phase 0 synthesized findings
├── data-model.md        # Phase 1 entity definitions
├── quickstart.md        # Phase 1 runbook for new gates/tests
├── contracts/           # Phase 1 schemas for quality gate artifacts
└── tasks.md             # Generated later via /speckit.tasks
```

### Source Code (repository root)
```
alphaforge-brain/
├── src/
│   ├── domain/run/               # Determinism, orchestrator, retention logic
│   ├── services/                 # Equity, execution, metrics services under test
│   ├── infra/                    # Cold storage, caching, utilities
│   └── scripts/ci/               # Quality gate + memory probe harnesses
├── scripts/contracts/            # Frontend contract verification scripts and helpers
├── tests/
│   ├── unit/services/            # Service-level coverage additions
│   ├── integration/run/          # Determinism + manifest validation suites
│   ├── perf/                     # Trust gate runtime benchmarks
│   └── ci/                       # Quality gate smoke/failure-path tests
└── scripts/bench/                # perf_run harness feeding perf gating

zz_artifacts/                     # Generated quality gate + perf summaries
artifacts/                        # Baseline perf + determinism references
```

**Structure Decision**: Leverage existing dual-root layout; implementation lives in `alphaforge-brain/src` and `alphaforge-brain/tests`, with supportive scripts under `scripts/ci` and `scripts/contracts`, and documentation under `specs/012-tests-enhancment-deliver/`.

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |

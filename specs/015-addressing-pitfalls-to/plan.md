## Technical Context Notes

- Benchmark baseline source confirmed during research: `artifacts/perf_baseline.json` with cross-check against `zz_artifacts/perf_latest.json`.
- Schema validation will leverage JSON Schema enforced via Python CI script.
- Observability integration reuses Prometheus/Alertmanager with new parquet fallback metrics.
- Waiver cadence automation parses `WAIVERS.md` and governance tracker into structured JSON for dashboards.
- Sweep acceptance harness relies on deterministic fixtures and frozen manifests under `alphaforge-brain/tests/sweeps`.
# Implementation Plan: Operational Guardrail Remediation

**Branch**: `015-addressing-pitfalls-to` | **Date**: 2025-10-14 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Restore governance guardrails by profiling the Masters validation pipeline, re-enabling automated benchmark alerts, hardening configuration validation, surfacing parquet fallback and waiver cadence telemetry, expanding sweep acceptance coverage, and documenting mitigation ownership so runtimes, trust gates, and governance processes stay within constitutional limits.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.11 (Poetry-managed) for backend automation; dashboards via existing observability stack (presumed Python + Prometheus metrics wiring).
**Primary Dependencies**: FastAPI services, pytest benchmarks, Prometheus client tooling, existing parquet doctor script, CI (GitHub Actions) with ruff/mypy.
**Storage**: SQLite artifacts, JSON/Parquet caches, Prometheus TSDB, governance tracker (existing SQLite/JSON).
**Testing**: pytest suites (benchmark harness, acceptance suites), property tests, CI schema validators.
**Target Platform**: Linux CI agents and developer workstations (Windows PowerShell support maintained), observability dashboards.
**Project Type**: Dual-root backend (`alphaforge-brain`) plus docs/zz_artifacts updates; no Mind changes beyond dashboards consuming metrics.
**Performance Goals**: Masters validation runtime ≤110% of baseline (SC-001), alert latency ≤15 minutes, parquet fallback alert dispatch ≤5 minutes, waiver backlog reduction ≥50% in quarter.
**Constraints**: Must maintain determinism and trust-gate compliance, zero waiver over 60 days, alerts must be actionable with minimal noise, schema validation cannot block legitimate changes without remediation path.
**Scale/Scope**: Single power-user backend with automation pipeline; sweep acceptance suites cover representative multi-ticker combinations and partial-cap cases.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I (Determinism First)**: Profiling and alert automation must be deterministic; no random sampling introduced. ✅ Plan enforces deterministic metrics and uses existing seeded pipelines.
- **Principle II (Test-First & Traceability)**: Every FR will map to new/updated tests (benchmark harness, CI validators, acceptance suites). ✅ Noted in Phase 1 deliverables.
- **Principle V (Observability & Forensic Auditability)**: Enhancements expand structured telemetry, preserving evidence. ✅ Alignment documented in spec.
- **Principle VI (Performance Discipline)**: Plan prioritizes performance profiling and baseline enforcement. ✅ Core objective.
- **Principle VIII (Documentation as Executable Interface)**: Runbook updates and quickstart required. ✅ Included in deliverables.
- **Principle IX (Multi-Project Architecture)**: Work limited to Brain backend + docs; no cross-root violations planned. ✅ Confirmed.
- **Waivers**: No existing waivers required; goal is to reduce waiver backlog. ✅

**Gate Verdict (Pre-Design)**: PASS — proceed to Phase 0.

**Post-Design Review** (after Phase 1 outputs):
- Design artifacts maintain deterministic flows and do not introduce Mind dependencies.
- Contracts restrict new endpoints to internal governance scope, preserving bounded contexts.
- Documentation deliverables ensure traceability and governance visibility.

**Gate Verdict (Post-Design)**: PASS — ready for Phase 2 planning.

## Project Structure

### Documentation (this feature)

```
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```
alphaforge-brain/
├── src/
│   ├── services/
│   │   ├── validation/
│   │   ├── trust_gates/
│   │   └── retention/
│   ├── benchmarks/
│   │   └── perf/
│   ├── infra/
│   │   └── cache/
│   └── orchestration/
├── scripts/
│   ├── bench/
│   ├── ci/
│   └── cli/
├── docs/
│   └── operations/
├── tests/
│   ├── benchmarks/
│   ├── governance/
│   ├── services/
│   └── sweeps/
└── zz_artifacts/

docs/
└── operations/

.github/workflows/
```

**Structure Decision**: Focus implementation within `alphaforge-brain/src/services`, `scripts/bench`, `scripts/ci`, `tests/*`, observability integrations under `infra/cache` and `zz_artifacts`, plus documentation updates in `docs/operations`; no frontend (Mind) changes required.

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |

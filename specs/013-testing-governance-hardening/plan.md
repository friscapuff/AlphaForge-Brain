# Implementation Plan: Testing Governance Hardening

**Branch**: `013-testing-governance-hardening` | **Date**: 2025-10-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/013-testing-governance-hardening/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Harden AlphaForge’s governance loop by transforming six compliance checks into enforced gates: versioned causality tolerance SLAs, mandatory validation go/no-go, schema-versioned persistence with migrations, accounting invariants, automated retention pinning defaults, and runtime dual-root import guards that stop untrustworthy runs from advancing.

## Technical Context

**Language/Version**: Python 3.11 (Poetry-managed virtualenv)
**Primary Dependencies**: FastAPI surfaces, Pydantic models, internal `services.trust_gates` suite, Masters validation engines, Prometheus client, Ruff/Mypy strict-plus overlays
**Storage**: SQLite artifacts, JSON manifests, Parquet exports (Brain project scope)
**Testing**: pytest + coverage, Masters validation harness, ruff + mypy strict-plus configs
**Target Platform**: Linux CI runners, developer macOS/Windows via Poetry, containerized production deployments
**Project Type**: Dual-root repository with backend `alphaforge-brain`; frontend untouched for this feature
**Performance Goals**: Trust-gate enforcement within ≤5s per run; retention sweep overhead <3%; schema validation latency <1s per insert; runtime guard negligible overhead
**Constraints**: Deterministic replay, zero Brain↔Mind imports, configuration-driven tolerances, waiver process for any bypass, <100MB additional RSS during gate execution
**Scale/Scope**: Applies to ~100 orchestrated runs weekly, ~500 retained runs, schema versions tracked across long-term archives

### Documentation (this feature)

```
specs/013-testing-governance-hardening/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
└── tasks.md
```

### Source Code (repository root)

```
alphaforge-brain/
├── src/
│   ├── services/
│   │   ├── trust_gates/
│   │   │   ├── suite_service.py
│   │   │   ├── telemetry.py
│   │   │   └── gates/
│   │   └── validation/
│   ├── domain/
│   │   └── run/
│   │       ├── orchestrator.py
│   │       └── retention_policy.py
│   ├── cli/
│   │   └── retention/
│   ├── models/
│   └── infra/
├── configs/
│   ├── trust_gates/
│   │   └── tolerances/
│   └── retention/
├── contracts/
│   └── persistence/
├── scripts/
│   ├── migrations/
│   └── ci/
└── tests/
    ├── services/
    │   ├── trust_gates/
    │   ├── validation/
    │   ├── retention/
    │   └── cli/
    ├── domain/
    │   └── run/
    └── imports/

alphaforge-mind/
└── (no changes for this feature)

shared/
└── (utilities leveraged only if cross-root safe)
```
│   └── ci/
└── tests/
  ├── services/
  │   ├── trust_gates/
  │   ├── validation/
  │   ├── retention/
  │   └── cli/
  └── integration/

alphaforge-mind/
└── (no changes for this feature)

shared/
└── (utilities leveraged only if cross-root safe)
```

**Structure Decision**: Implementation stays within `alphaforge-brain` services, configs, contracts, scripts, and tests; `alphaforge-mind` untouched except documentation references mandated by Principle VIII.

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| _None_ | N/A | Existing architecture satisfies needs |

## Coverage Strategy

### Verification Layers
- **Contract & Config Guards**: JSON Schema validation, tolerance YAML parsing, and retention policy linting run via `pytest` suites (`test_persistence_schema_version.py`, `test_causality_tolerances.py`) before implementation merges.
- **Service Enforcement Tests**: Trust gate, validation pipeline, accounting invariants, and retention policy suites assert `RunValidationStatus` transitions and audit side effects with Prometheus counter fakes.
- **Interface & CLI Coverage**: API promotion conflict tests and retention CLI specs ensure governance flows remain enforced from external entrypoints.
- **Runtime Guardrails**: Import hook tests (unit + integration) protect Brain↔Mind separation, complementing lint coverage.

### Evidence & Reporting
- **Coverage Thresholds**: Maintain ≥90% statement coverage for touched modules; capture deltas via `pytest --cov=alphaforge_brain --cov-report=xml` and archive per phase as `zz_artifacts/coverage/governance/phase_<n>.xml`.
- **Artifact Bundles**: Store gating transcripts (failed run manifests, audit logs) alongside coverage XML, linking run hashes to test executions.
- **Metrics Snapshot**: Record Prometheus counter outputs during regression runs and attach to release notes to satisfy SC-001…SC-005 observability requirements.
- **Sign-off Checklist**: Phase 6 tasks must capture coverage evidence for every FR/SC, ensure artifacts are documented, and confirm any Constitution updates or waivers for FR-012 are filed.

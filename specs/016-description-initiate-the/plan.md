# Implementation Plan: Enriching Journaling Detail, Quality, and Visualizations

**Branch**: `016-description-initiate-the` | **Date**: 2025-10-15 | **Spec**: `specs/016-description-initiate-the/spec.md`
**Input**: Feature specification from `/specs/016-description-initiate-the/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Extend AlphaForge Brain journaling so each CompletedTrade, Fill, and run-level aggregate carries deterministic signal metadata, risk annotations, and context snapshots while tightening trust-gate + retention enforcement. We will introduce enriched data models, schema-versioned artifacts, and validation hooks that fail closed whenever journaling evidence is missing, preparing downstream consumers (including Mind) without changing existing frontend code.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.11 (Poetry-managed env)
**Primary Dependencies**: Pydantic v2 models, internal `alphaforge_brain` services/pipelines, FastAPI surfaces, Prometheus client, pandas/numpy for aggregates
**Storage**: SQLite (`studio.db` artifacts), JSON/Parquet exports under `zz_artifacts/` (Brain scope)
**Testing**: pytest + coverage, Masters regression harness, trust-gate validation suites
**Target Platform**: Linux CI runners & developer workstations; headless execution in alphaforge-brain pipelines
**Project Type**: Backend simulation / analytics (alphaforge-brain bounded context)
**Performance Goals**: Trust-gate journaling validation completes ≤5s per run; additional artifact generation adds ≤3% runtime overhead measured against the 40s benchmark captured in `zz_artifacts/perf_latest.json` (see research Decision 1).
**Constraints**: Deterministic hashing, tolerance profile enforcement, retention budgets for journaling artifacts aligned with `configs/retention/policy.yaml` (see research Decision 2).
**Scale/Scope**: Supports nightly + research runs producing up to 15k trades per strategy with bursts of up to eight concurrent trust-gate evaluations and ~50 fills per run (see research Decision 3).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Trust-gate tolerance profiles: document required updates to journaling tolerance YAML, confirm signed change-log entries, and plan validation tasks that fail closed when enriched fields regress.
- Retention enforcement: map enriched artifact locations to `configs/retention/policy.yaml`, specify sweep evidence in `zz_artifacts/retention/`, and ensure pin/unpin audit flows remain intact.
- Runtime import guard: verify Brain-only changes respect dual-root boundaries, include lint + runtime checks in risk analysis, and describe remediation if new shared modules are introduced.
- Coverage ≥90%: outline test additions (unit, integration, negative-path trust gate fixtures) that keep global coverage and failure seeding intact.
- Automated waiver discipline: plan waiver creation/expiry monitoring in case temporary exceptions are needed for retention or trust-gate metrics and ensure burn-down cadence is documented.

## Project Structure

### Documentation (this feature)

```
specs/016-description-initiate-the/
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
│   └── alphaforge_brain/
│       ├── artifacts/
│       ├── models/
│       ├── pipelines/
│       ├── services/
│       └── trust_gates/
├── tests/
│   ├── integration/
│   ├── pipelines/
│   ├── regression/
│   └── trust_gates/
└── scripts/

shared/
└── instrumentation/

zz_artifacts/
└── journaling/
```

**Structure Decision**: Work stays within `alphaforge-brain` models/services/pipelines and associated tests, producing artifacts under `zz_artifacts/journaling/`. No Mind (frontend) code changes; shared utilities touched only if unavoidable and must retain import-guard compliance.

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |

## Phase 0 – Research Outline

### Open Questions (from Technical Context)
- ✅ Baseline runtime window for journaling validation to measure the ≤3% overhead target (answered in `research.md`, Decision 1).
- ✅ Exact retention storage thresholds and pin/unpin rules applicable to enriched journaling artifacts (answered in `research.md`, Decision 2).
- ✅ Expected maximum concurrent runs (and trade volume) that influence retention sweeps and aggregation scaling (answered in `research.md`, Decision 3).

### Research Tasks
- Research baseline runtimes: Inspect recent Masters/trust-gate perf artifacts to establish representative journaling validation durations and variance.
- Document retention thresholds: Review `configs/retention/policy.yaml`, governance docs, and prior waiver records to capture storage budgets and pin workflows.
- Quantify concurrent run expectations: Interview pipeline scheduling artifacts/Docs to determine peak run counts and trade volumes for capacity planning.
- Best practices: Identify deterministic hashing + schema evolution techniques for Pydantic models handling large journaling payloads.
- Integration patterns: Capture how existing trust-gate services ingest artifact metadata so enriched schemas plug in without breaking fail-closed behavior.

### Deliverable
- `research.md` consolidating decisions, rationale, and alternatives for the above.

## Phase 1 – Design & Contracts

### Planned Outputs
- `data-model.md` defining Updated `CompletedTrade`, `Fill`, `TradeContextSnapshot`, and `JournalingAggregate` schemas with validation + relationships.
- `contracts/` containing versioned JSON Schema (and optional OpenAPI excerpts) for journaling artifacts/aggregates.
- `quickstart.md` describing how to generate, validate, and inspect the enriched artifacts with CLI or pipeline snippets.

### Key Design Considerations
- Schema versioning and compatibility strategy for new fields (align with Constitution X).
- Trust-gate validation hooks covering negative-path cases and Prometheus telemetry integration.
- Retention workflow alignment, including evidence artifact locations and breach logging procedures.
- Aggregation cost + batching approach to stay within performance envelopes.

### Agent Context Update
- After drafting design artifacts, run `.specify/scripts/powershell/update-agent-context.ps1 -AgentType copilot` to append new references for journaling schemas and tooling.

## Phase 2 – Implementation Prep (Preview)

- Define task breakdown in subsequent `/speckit.tasks` run: model migrations, pipeline enrichment, artifact writers, trust-gate extensions, retention automation updates, test suites, docs.
- Identify prerequisites for implementation (e.g., backfilling historical artifacts, coordinating with governance for tolerance updates).
- Confirm no Constitution gates remain unresolved before moving to tasks.

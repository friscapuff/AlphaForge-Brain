# Implementation Plan: Trust Gate Framework

**Branch**: `011-trust-gate-framework` | **Date**: 2025-10-11 | **Spec**: [`spec.md`](./spec.md)
**Input**: Feature specification from `/specs/011-trust-gate-framework/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → If not found: ERROR "No feature spec at {path}"
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → Detect Project Type from context (single, web(frontend+backend), mobile, or dual-project brain+mind)
   → Set Structure Decision based on project type
3. Fill the Constitution Check section based on the content of the constitution document (v1.1.0 or later).
4. Evaluate Constitution Check section below
   → If violations exist: Document in Complexity Tracking
   → If no justification possible: ERROR "Simplify approach first"
   → Update Progress Tracking: Initial Constitution Check
5. Execute Phase 0 → research.md
   → If NEEDS CLARIFICATION remain: ERROR "Resolve unknowns"
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, agent-specific template file
7. Re-evaluate Constitution Check section
   → If new violations: Refactor design, return to Phase 1
   → Update Progress Tracking: Post-Design Constitution Check
8. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
9. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary
Deliver a deterministic trust gate harness for AlphaForge Brain that executes golden-run determinism, causality, ingest idempotency, timezone normalization, universe stamp, equity reconciliation, and accounting gates through a single CLI/CI command. Persist signed trust reports alongside Masters validation artifacts so any failing gate blocks promotion until remediated or waived.

## Technical Context
**Language/Version**: Python 3.11 (per `pyproject.toml`)
**Primary Dependencies**: structlog, numpy/pandas, pyarrow, exchange-calendars, SQLAlchemy, FastAPI CLI surface, existing Masters validation modules, Prometheus metrics
**Storage**: SQLite manifests, Parquet/Arrow datasets, signed JSON artifacts under `zz_artifacts/`
**Testing**: pytest, pytest-asyncio, hypothesis property suites, benchmark harness (`scripts/bench/perf_run.py`)
**Target Platform**: AlphaForge Brain CLI in CI/Linux + local Windows runners, surfaced to Mind via API payloads
**Project Type**: brain+mind dual (Brain runs trust gates, Mind displays pass/fail badges)
**Performance Goals**: Trust suite runtime ≤ 1.5× Masters validation baseline; each gate completes ≤120 s; maintain existing validation SLA (34 ms ×1.2 guard) by running in parallel where safe
**Constraints**: Fully deterministic artifacts (hash-stable, seedable datasets), tolerance-configured failure thresholds, no Brain↔Mind coupling beyond contracts, governance waivers for overrides, reproducible ingest snapshots
**Scale/Scope**: Equity universes up to ~10k symbols across multi-year bars (~10 GB ingest snapshots); leak-catcher datasets ≤100 MB; accounting reconciliations over millions of trades per run

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Determinism** ✅ Golden-run baseline + leak-catcher seeds documented; artifacts signed and hash-validated.
- **Test-First** ✅ Plan mandates failing tests per FR (gate harness, manifest persistence, CLI) before implementation.
- **Modular MVC / Dual Root** ✅ All logic in Brain; Mind only reads status fields via contracts.
- **Observability** ✅ structlog spans + Prometheus metrics per gate; follow constitution requirement V & VI.
- **Contract Versioning** ✅ New trust report schema versioned under `contracts/trust_gates/v1`; MAJOR bump tracked if payload changes impact Mind.
- **Performance Targets** ✅ Runtime guardrails defined; integrate into benchmark harness for enforcement.
- **Data Integrity** ✅ New artifacts avoid schema drift; any DB tables added include migrations + checksum validation.
- **Validation Defaults** ✅ Trust suite runs ahead of Masters gating, records thresholds, and enforces waiver policy for deviations.

Initial gate status: **PASS**.

**Post-Design Review (2025-10-11)**: Data model, contracts, and quickstart confirm determinism, observability, and governance commitments remain satisfied. No additional waivers required → **PASS**.

## Project Structure

### Documentation (this feature)
```
specs/[###-feature]/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
└── tasks.md
```

### Source Code (repository root)
```
# Option 1: Single project (DEFAULT legacy)
src/
  models/
  services/
  cli/
  lib/

tests/
  contract/
  integration/
  unit/

# Option 2: Web application (frontend + backend)
backend/
  src/
    models/
    services/
    api/
  tests/
frontend/
  src/
    components/
    pages/
    services/
  tests/

# Option 3: Mobile + API
api/
  src/
  tests/
ios/ or android/
  src/
  tests/

# Option 4: Dual Project (AlphaForge Brain + AlphaForge Mind)
alphaforge-brain/
  src/
  tests/
alphaforge-mind/
  src/
  tests/
shared/ (optional strictly pure utilities)
```

**Structure Decision**: Dual project — Brain produces trust gate artifacts and CLI; Mind consumes status via API/manifest only.

## Phase 0: Outline & Research
- Inventory current determinism + Masters harness entrypoints (`services.cli.run_hash`, validation pipelines) to locate integration hooks.
- Collect existing golden-run baselines, leak-catcher datasets, ingest manifests, and timezone adapters; document completeness and regeneration workflow.
- Interview ingest owners for vendor versioning, retry semantics, and cache lineage; capture references for idempotency testing.
- Trace accounting reconciliation pipeline (PnL ledger, cost models, equity curves) to map data sources and tolerances.
- Specify metrics + observability requirements (structlog fields, Prometheus labels) and audit retention policies.
- Confirm governance requirements (waivers, documentation) and identify open research questions to resolve before design kickoff.

## Phase 1: Design & Contracts
- Draft `data-model.md` with TrustGateSuite, TrustGateResult, GoldenRunBaseline, LeakCatcherDataset, UniverseStamp schemas + relationships.
- Define CLI contract (`poetry run trust-gates` flags, exit codes, env overrides) and map to service layer orchestration.
- Specify artifact persistence (signed JSON, SQLite tables) and manifest extension fields; include version tags and checksum strategy.
- Model per-gate executor interfaces, dependency injection boundaries, and deterministic dataset acquisition flows.
- Outline observability integration (structlog event schema, Prometheus metrics) and document in `quickstart.md` for local replay.
- Capture Mind consumption contract adjustments (API payload fields, status badges) ensuring no Mind-side execution logic.
- Prepare design review notes for post-design constitution re-check (determinism, performance, contract versioning impacts).

## Phase 2: Task Planning Approach
- Use `/tasks` to expand FR-aligned backlog; tag each task with `alphaforge-brain`, `docs/`, or `alphaforge-mind` as applicable.
- Group tasks by gate (determinism, causality, ingest, timezone, universe, equity/accounting) plus shared harness/observability tracks.
- For every FR (201–213), include failing test creation, implementation, documentation, and benchmarking subtasks.
- Create dedicated tasks for governance artifacts (WAIVERS update, docs/operations/trust_gates.md alignment) and release gating.
- Reserve slots for performance validation tasks (extend `bench:perf_run`, add per-gate telemetry assertions).

## Phase 3+: Future Implementation
[Same]

## Complexity Tracking
| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| _None_ | – | – |

## Progress Tracking
**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Task planning complete (/plan command - describe approach only)
- [x] Phase 3: Tasks generated (/tasks command)
- [x] Phase 4: Implementation complete
- [x] Phase 5: Validation passed (see [`validation_evidence.md`](./validation_evidence.md))

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [ ] Complexity deviations documented

---
*Based on Constitution v1.3.0 - See `/memory/constitution.md`*

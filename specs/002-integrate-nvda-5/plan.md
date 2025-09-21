# Implementation Plan: NVDA 5-Year Historical Dataset Integration

Branch: 002-integrate-nvda-5
Status: Active (Phases A–C complete; Phase D in progress; Phase J generalization planned)

## Phase 0: Research
- Artifact: `research.md` (dataset characteristics, anomalies, normalization steps, reproducibility and risks) – COMPLETE

## Phase 1: Data Model & Contracts
- Artifact: `data-model.md` – COMPLETE
- Artifact: `contracts/openapi.yaml` (additive enrichment) – COMPLETE
- Artifact: `quickstart.md` – COMPLETE

## Phase 2: Task Breakdown
- Artifact: `tasks.md` – COMPLETE

## Progress Tracking
| Phase | Artifact(s) | Status | Notes |
|-------|-------------|--------|-------|
| 0 | research.md | COMPLETE | Captures anomaly taxonomy & policies |
| 1 | data-model.md, contracts/openapi.yaml, quickstart.md | COMPLETE | OpenAPI additive (data_hash/calendar) |
| 2 | tasks.md | COMPLETE | 50 enumerated tasks A01..I05 |
| A | T001–T013 | COMPLETE | Ingestion & normalization implemented |
| B | T014–T018 | COMPLETE | Validation & artifacts integrated |
| C | T019–T022 | COMPLETE | Indicator alignment & tests |
| D | T023–T024 | PARTIAL | Strategy & E2E run passing; risk/execution tests pending |

## Execution Gates
- Ambiguities Resolved: YES (see spec.md Clarification Decisions)
- Constitutional Alignment: YES (determinism, realism-lite, extensibility, transparency)
- Additive Contract Only: YES (no breaking schema removals)

## High-Level Sequence (Implementation Ordering)
1. Ingestion & normalization (A01–A13)
2. Validation artifact + manifest enrichment (B01–B05)
3. Feature/indicator alignment & tests (C01–C04)
4. Strategy/risk/execution integration tests (D01–D05)
5. Metrics & additional validation tests (E01–E05)
6. API serialization & contract alignment (F01–F05)
7. Idempotency & retention adjustments (G01–G03)
8. Tooling/scripts & regression tests (H01–H05)
9. Quality gates, changelog, release prep (I01–I05)

## Risks & Mitigations
| Risk | Mitigation |
|------|------------|
| Timezone mis-normalization | Explicit conversion test t -> UTC with known fixture |
| Calendar misclassification | Unit test injecting known holiday & non-holiday gap |
| Hash instability | Canonical serialization (sorted columns, stable dtypes) test |
| Performance regression | Benchmark ingestion (E05) baseline recorded |

## Success Criteria
- All tasks A01–I05 checked
- New tests deterministic (repeat runs identical)
- OpenAPI diff additive only
- validation.json present with anomaly counters
- RunDetail includes data_hash, calendar_id, validation_summary subset

## Out-of-Scope Confirmation
- No multi-asset portfolio logic added
- No corporate action adjustment
- No real-time incremental ingestion

## Next Step
Execute remaining Phase D tasks (T025–T027) then proceed with Phase J (generalization: DataSource abstraction, registry, multi-symbol readiness) before continuing to metrics (Phase E).

## Forthcoming Phase J (Generalization Preview)
Planned additions: DataSource protocol, LocalCsvDataSource, dataset registry (symbol,timeframe), generic CSV ingestion refactor, orchestrator registry integration, manifest enrichment (symbol,timeframe), run hash binding to data snapshot, tests for multi-symbol cache isolation & missing symbol error paths.


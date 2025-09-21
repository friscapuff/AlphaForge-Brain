# Implementation Plan: NVDA 5-Year Historical Dataset Integration

Branch: 002-integrate-nvda-5
Status: Active (Phases A–D complete; Phase J generalization & typing hardening in progress)

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

## Phase J: Generalization & Typing Hardening

Objective: Remove single-asset (NVDA) assumptions, introduce pluggable data source abstraction, and lock a zero-error static analysis baseline (mypy + Ruff) to future-proof multi-symbol and provider expansion.

### J1 Foundation (Completed)
| Task | Status | Outcome |
|------|--------|---------|
| G01 Remove synthetic orchestrator candles | COMPLETE | Orchestrator always sources real dataset slices. |
| G02 DataSource protocol + LocalCsvDataSource | COMPLETE | Unified interface for local CSV providers. |
| G03 Dataset registry (symbol,timeframe → metadata) | COMPLETE | Declarative mapping enables rapid symbol onboarding. |
| G04 Generic CSV ingestion refactor | COMPLETE | Eliminated NVDA-specific branching; pure path + calendar driven. |
| G05 Orchestrator integration with registry/DataSource | COMPLETE | Run pipeline dynamically resolves data source. |
| G06 Manifest enrichment (symbol, timeframe) | COMPLETE | Artifacts carry dataset identity for reproducibility. |
| G07 Run hash dataset snapshot binding | COMPLETE | Hash stability tied to per (symbol,timeframe) data_hash. |
| G08 API provider stub | COMPLETE | Placeholder extension surface for remote providers. |

### J2 Validation & Functional Tests (Completed)
| Task | Status | Outcome |
|------|--------|---------|
| G09 Multi-symbol cache isolation test | COMPLETE | Ensures independent caching; no cross-symbol contamination. |
| G10 Missing symbol/timeframe error test | COMPLETE | Clear failure mode & message integrity. |

### J3 Typing & Lint Hardening (In Progress)
| Task | Status | Notes |
|------|--------|-------|
| G11 Elevate mypy to strict for src + tests | COMPLETE | Strict enforced in pyproject; baseline zero errors in src. |
| G12 Annotate remaining dynamic modules | COMPLETE | Ingestion edges, validation summary, feature engine stabilized. |
| G13 Annotate all tests & fixtures | IN PROGRESS | Run-level tests partially annotated; remaining test modules queued. |
| G14 Modernize typing syntax | PENDING | Will convert legacy typing.List/Dict to builtin generics & PEP 604 unions. |
| G15 Enable extra mypy warnings | PENDING | Will activate warn-redundant-casts, warn-unused-ignores. |
| G16 Expand Ruff ruleset | PENDING | Add bugbear, pyupgrade (strict), safety rules. |
| G17 CI mypy snapshot gate | PENDING | JSON snapshot + diff fail on >0 errors. |
| G18 Pre-commit selective mypy hook | PENDING | Fast feedback on staged Python files. |
| G19 Mypy error diff script | PENDING | Generates markdown (expected empty post-hardening). |
| G20 Docs: Typing & Lint Guarantees | PENDING | README & spec updates to guide contributors. |
| G21 Benchmark typing+lint duration | PENDING | Wall clock recorded; soft regression watch. |
| G22 Audit remaining type: ignore | PENDING | Each ignore carries rationale or is removed. |

### Phase J Acceptance Criteria
- Zero mypy errors (src + tests) with strict + extra warnings enabled.
- Ruff expanded rules clean (no unaddressed findings in target categories).
- Added abstraction introduces no behavioral diffs in existing NVDA runs (hash & artifact parity confirmed).
- Manifest & run hash deterministically reflect multi-symbol dataset identity.
- Documentation enumerates guarantees & contributor typing policy.
- No unjustified type: ignore directives remain.

### Rationale
Executing abstraction and typing hardening together avoids duplicate churn on evolving interfaces and ensures any future provider integrations sit atop a stable, statically verified contract.

### Follow-On (Post Phase J)
Proceed to Metrics & Validation Extensions (Phase E tasks) with confidence that multi-symbol + typing foundations are locked and reproducible.


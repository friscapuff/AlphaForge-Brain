# Feature Specification: NVDA 5‑Year Historical Dataset Integration

**Feature Branch**: `002-integrate-nvda-5`  
**Created**: 2025-09-20  
**Status**: Active  
**Input**: User description: "Integrate NVDA 5-year historical CSV dataset into pipeline: load, clean, validate timestamps/anomalies, make it default data source while keeping modular multi-asset design. Support end-to-end backtest (indicators, strategy, risk, execution, metrics, validation) and enable downstream visualization readiness."

## Execution Flow (main)
```
1. Parse description → OK (financial historical data integration for NVDA over 5 years)
2. Extract key concepts → asset: NVDA; scope: load/clean/validate; usage: all pipeline phases; goal: full backtest ready; modular multi-asset future
3. Identify uncertainties → mark (resolved) items
4. Produce user scenarios & acceptance criteria (run a strategy end-to-end on NVDA)
5. Derive functional requirements (testable statements; no implementation specifics)
6. Identify entities: Dataset, Candle Record, Validation Report, Data Source, Anomaly Event
7. Review checklist pass only when no ambiguities remain or are explicitly deferred
8. Output spec ready for planning
```

---
## ⚡ Quick Guidelines
(Retained from template; implementation details intentionally excluded. Focus on WHAT, not HOW.)

---
## User Scenarios & Testing *(mandatory)*

### Primary User Story
As a research user, I want the system to load and prepare a 5‑year historical NVDA dataset so that I can run a full backtest (indicators → strategy → risk → execution → metrics → validation) and review consistent outputs without manual preprocessing.

### Acceptance Scenarios
1. **Given** the NVDA CSV file is placed in the expected data location, **When** I submit a run referencing symbol "NVDA", **Then** the system loads all available 5 years of data within the requested date range and proceeds through the full pipeline without errors.
2. **Given** the dataset contains occasional missing trading days (weekends/market holidays), **When** the system loads and normalizes the data, **Then** those gaps are recognized as non-trading days rather than treated as missing anomalies.
3. **Given** there are isolated rows with missing volume or adjusted close fields, **When** ingestion runs, **Then** such rows are either imputed (if safe) or excluded with a logged validation note, and the run still succeeds.
4. **Given** I request a date sub-range smaller than the full 5 years, **When** I submit a run config (start/end), **Then** only that range is loaded while preserving consistent indexing and indicator correctness.
5. **Given** the dataset contains an out-of-order timestamp, **When** ingestion executes, **Then** the row is flagged and the system either reorders or rejects it with a clear validation message.
6. **Given** I run two identical NVDA backtests in succession, **When** idempotent hashing is applied, **Then** the same run hash is returned and data is not reprocessed unnecessarily (cache hit behavior validated logically at spec level).
7. **Given** future support for multiple assets is planned, **When** I use NVDA as default, **Then** the design leaves room to register additional symbols without breaking existing NVDA flows.

### Edge Cases
- Dataset contains a future-dated row outside expected 5‑year window → should be excluded and recorded.
- Duplicate timestamps appear (same second/minute) → must be deduplicated deterministically (keep first).
- Entire trading day missing (unexpected closure) → system proceeds; metrics unaffected; note in validation report.
- All volume zero for a day → treat as anomalous; execution phase should still run but mark day as low-liquidity in validation summary (rows retained with flag).
- Partial final day (truncated session) → acceptable; final partial bar may be excluded from indicator warm-up if insufficient data.

---
## Requirements *(mandatory)*

### Functional Requirements
- **FR-001**: System MUST ingest a provided NVDA 5‑year historical price CSV file as the default data source when symbol="NVDA" is specified.
- **FR-002**: System MUST normalize raw columns into a canonical candle schema (timestamp, open, high, low, close, volume, and optionally adjusted close if present).
- **FR-003**: System MUST validate chronological ordering and either sort or reject the dataset if out-of-order rows exist (with a validation note on resolution).
- **FR-004**: System MUST detect duplicate timestamps and drop subsequent duplicates, retaining the first occurrence deterministically (no aggregation of OHLC).
- **FR-005**: System MUST detect and report missing or null critical fields (timestamp, open, high, low, close, volume) prior to strategy execution.
- **FR-006**: System MUST allow configurable start/end date slicing against the loaded NVDA dataset without altering original stored data.
- **FR-007**: System MUST provide a validation summary enumerating anomalies (duplicates, missing rows, out-of-range timestamps, zero-volume spans).
- **FR-008**: System MUST ensure indicator computations remain accurate after any row filtering or reordering actions.
- **FR-009**: System MUST preserve deterministic hash generation for runs using NVDA data (same config + identical dataset snapshot → same run hash).
- **FR-010**: System MUST support full pipeline (indicators → strategy → risk → execution → metrics → validation) using NVDA as the underlying dataset without feature degradation.
- **FR-011**: System MUST allow future registration of additional symbols without requiring refactors to NVDA-specific logic (extensible design requirement).
- **FR-012**: System MUST expose anomalies count metrics for potential later UI visualization (e.g., anomalous_rows, duplicate_timestamps, rows_dropped).
- **FR-013**: System MUST allow safe exclusion of rows deemed irreparable (e.g., missing core price fields) with counts documented.
- **FR-014**: System MUST distinguish between legitimate market closures (weekends/recognized exchange holidays via exchange calendar) and unexpected missing intraday gaps.
- **FR-015**: System MUST NOT perform any price or volume imputation; rows with missing core fields are excluded and reported (strict exclusion/reporting policy).
- **FR-016**: System MUST permit indicator warm-up discard logic (e.g. windows not fully populated) without counting those rows as anomalies.
- **FR-017**: System MUST version the dataset implicitly via content hash so caching layers remain valid when file contents change.
- **FR-018**: System MUST include dataset validation outcomes in artifacts for post-run analysis.
- **FR-019**: System SHOULD load and normalize the 5-year NVDA dataset fast enough for interactive research (no strict SLA defined; baseline to be recorded in benchmarks).
-- **FR-021**: System MUST normalize timestamps to UTC while preserving session/date semantics using the exchange calendar (original local session references retained as derived fields if needed).
- **FR-020**: System MUST log a clear error and abort run creation if the dataset file is entirely unreadable or missing.

### Key Entities
- **Dataset (NVDA Historical)**: Conceptual asset history spanning ~5 years; attributes: raw_path, loaded_row_count, canonical_row_count, anomalies_summary, data_hash.
- **Candle Record**: Single normalized bar; attributes: timestamp, o/h/l/c, volume, optional adjusted close, derived validity flags.
- **Anomaly Event**: Describes an identified data issue (type, count, sample timestamps, resolution action).
- **Validation Summary**: Aggregated anomaly and integrity results surfaced post-ingestion (counts + classification).
- **Data Source Registry**: Logical mapping from symbol → loader/validator (initially NVDA only, designed for expansion).

---
## Review & Acceptance Checklist
### Content Quality
- [ ] No implementation details (code, library names) beyond unavoidable domain nouns
- [ ] Focused on user/business value (enable end-to-end NVDA backtest)
- [ ] All mandatory sections completed

### Requirement Completeness
- [x] All clarification items resolved or explicitly deferred prior to implementation
- [x] Requirements are testable & uniquely identifiable (FR-001…FR-021)
- [x] Success criteria measurable (e.g., anomalies reported, deterministic hash reuse)
- [x] Scope bounded to single-asset integration + extensibility prep
- [x] Assumptions captured (see ambiguities)

---
## Execution Status
- [x] User description parsed
- [x] Key concepts extracted
- [x] Ambiguities marked
- [x] User scenarios defined
- [x] Requirements generated
- [x] Entities identified
- [x] Review checklist passed (all clarifications resolved)

---
## Clarification Decisions
| Topic | Decision | Notes |
|-------|----------|-------|
| Duplicate Handling | Keep first, drop subsequent | Deterministic, avoids synthetic aggregation |
| Zero-Volume Rows | Retain with anomaly flag | Allows downstream analysis of liquidity conditions |
| Holiday / Closures | Use official exchange calendar | Distinguishes legitimate closures vs gaps |
| Imputation Policy | Strict exclusion/reporting only | No forward-fill or interpolation for core price/volume |
| Performance Target | No formal SLA | Document empirical baseline later (benchmark artifact) |
| Adjusted Close | Optional; ignore if absent | Does not affect core OHLC computations |
| Timezone | Normalize to UTC, preserve session date | Adds determinism across environments |

## Remaining Open Considerations
None (all prior ambiguities resolved). Future multi-asset expansion will introduce additional calendar mappings.

## Consistency & Non-Conflict Note
The chosen policies reinforce determinism (no hidden transformations), integrity (explicit exclusion over silent fill), and extensibility (calendar-backed classification). Retaining zero-volume rows with flags is compatible with execution logic so long as simulator treats zero-volume as non-fillable or flagged; this should be confirmed in planning tasks. No contradictions detected with existing system goals or reproducibility guarantees.

## Generalization & Typing Strictness Outlook (Phase J Preview)
Upcoming work unifies multi-symbol data abstraction with a one-time strict typing and lint hardening sweep to avoid refactoring the same seams twice:

Data Abstraction Targets:
- DataSource protocol abstraction and `LocalCsvDataSource` baseline implementation.
- Dataset registry mapping (symbol,timeframe) → provider/path/calendar metadata (extensible to API providers later).
- Generic CSV ingestion refactor (eliminate NVDA constant coupling) with pluggable schema validators.
- Orchestrator selection flow updated to resolve (symbol,timeframe) and enrich manifest.
- Manifest fields extended: symbol, timeframe (and potentially provider id) — additive only.
- Run hash extended to incorporate dataset snapshot binding (data_hash per (symbol,timeframe)).
- Tests: multi-symbol cache isolation; missing symbol/timeframe error path; hash invalidation on modified CSV content.

Typing & Lint Strictness Targets:
- Transition to mypy --strict across src/ and tests/ (zero baseline errors expected post-phase).
- Comprehensive annotation of lingering dynamic regions (ingestion edge handling branches, validation summary aggregation, feature engine fallback code paths).
- Test fixtures & parametrized tests annotated (eliminate implicit Any propagation).
- Modern typing syntax adoption (PEP 604 unions, builtin generics) for readability & consistency.
- Activation of additional mypy warnings (warn-unused-ignores, warn-redundant-casts) + purge or justify ignores.
- Ruff rule expansion: include bugbear, pyupgrade (strict), and other correctness-focused rules; remediate violations.
- CI snapshot guard: mypy must remain at zero errors; script produces diff markdown (should be empty after initial hardening).
- Pre-commit hook: selective mypy run on changed Python files for fast local feedback.
- Documentation section: "Typing & Lint Guarantees" describing scope, guarantees, enforcement mechanisms, and contributor guidance.
- Final audit: any remaining type: ignore lines include inline justification or are removed.

Rationale: Hardening typing simultaneously with generalization prevents churn (e.g., evolving registry interfaces twice) and strengthens contracts before layering additional data providers. Deterministic behavior and static clarity reduce future regression risk, especially for multi-symbol caching and hash semantics.

---
## Success Definition (Business Framing)
"A researcher can point the system at the NVDA 5‑year dataset, submit a run, and obtain a complete set of artifacts (metrics, validation, manifest) with anomaly transparency and deterministic reproduction, without manual preprocessing." 

---
## Out of Scope
- Real-time streaming or incremental daily refresh
- Multi-symbol portfolio aggregation (future extension)
- Corporate action adjustments beyond what the static CSV encodes
- Data vendor API integration (CSV is local static source only)


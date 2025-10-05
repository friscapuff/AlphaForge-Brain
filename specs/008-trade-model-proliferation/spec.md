# Feature Specification: Unified Trade & Equity Consistency Initiative

**Feature Branch**: `008-trade-model-proliferation`
**Created**: 2025-10-01
**Status**: Draft
**Input**: User description: "Trade model proliferation increases cognitive load; unify nomenclature (Fill, ExecutedTrade, CompletedTrade) with explicit boundaries. EquityBar vs ORM Equity divergence (exposures vs realized/unrealized pnl) suggests need for a reconciliation or second derived projection layer. NAV scaling placeholder (division by 1_000_000) is an arbitrary heuristic; should formalize equity units or notional basis. Validation gating (caution threshold) not fully integrated into pipeline decisioning (only computed; no gating actions). Duplicate metrics logic between legacy services.metrics and domain.metrics.calculator — converge into one canonical path. Determinism risk: floating drawdown tolerance hard-coded (1e-9) might become brittle across platforms if extended numeric operations added. Walk-forward config includes optimization scaffolding but execution path for parameter grid not visible; spec alignment pending. Multiple metrics hashing entrypoints: ensure single source-of-truth ordering and coverage (exposure, trade count, etc.) to prevent drift."

## User Scenarios & Testing *(mandatory)*

### Primary User Story
As a quantitative strategy developer or platform maintainer, I need a single, unambiguous domain language for execution lifecycle data (fills, aggregated trades, equity path, metrics & validation outcomes) so that I can extend or audit the system without reverse‑engineering overlapping models or risking determinism regressions.

### Acceptance Scenarios
1. **Given** a completed backtest run, **When** I inspect persisted artifacts and ORM tables, **Then** I can map each persisted record to exactly one documented lifecycle stage (Fill, CompletedTrade, EquityBar, MetricsSummary) with no ambiguous duplicate constructs.
2. **Given** a backtest that triggers a validation p-value below configured caution threshold, **When** the pipeline completes, **Then** the run status or returned payload explicitly conveys a caution flag and downstream retention/UX surfaces it.
3. **Given** two identical runs executed on different machines, **When** equity & metrics hashes are computed, **Then** the hashes match and are derived from a single canonical hashing module.
4. **Given** a strategy producing zero trades, **When** equity normalization occurs, **Then** NAV semantics remain consistent (no arbitrary million-scaling) and metrics reflect a neutral baseline deterministically.
5. **Given** a walk‑forward configuration containing an optimization grid, **When** the orchestrator processes the run, **Then** optimization either executes per spec or the run fails early with an explicit unsupported warning (no silent ignore).

### Edge Cases
- Backtest produces sparse intermittent fills (gaps in bars) → CompletedTrade aggregation logic must not fabricate holding periods incorrectly.
- Zero or single fill (no round‑trip) → CompletedTrade set may be empty; equity curve still valid.
- Validation distributions empty (user disabled) → Gating logic must not emit false caution.
- Extreme floating point precision (very small drawdowns) → Drawdown reconciliation tolerant within configurable epsilon.
- High cardinality optimization grid → Early guardrails on max combinations (prevent explosion) with clear error.

## Requirements *(mandatory)*

### Functional Requirements
- **FR-001**: System MUST define and document exactly three execution lifecycle abstractions: Fill (atomic), CompletedTrade (entry/exit aggregate), EquityBar (per-bar portfolio snapshot).
- **FR-002**: System MUST remove or refactor any additional ad-hoc Trade/Position dataclasses so that only the canonical abstractions remain or are clearly adapter mappers.
- **FR-003**: System MUST introduce a DeterministicEquityNormalizer that eliminates the 1_000_000 scaling heuristic and enforces a declared base currency/notional policy (documented constant or config).
- **FR-004**: System MUST apply validation caution threshold gating to run output: payload includes `validation_caution: boolean` and (if true) a list of triggering metrics.
- **FR-005**: System MUST consolidate metrics computation into a single module (`services.metrics_core` or equivalent) that is the only public entrypoint for metrics & equity hashing.
- **FR-006**: System MUST expose a configurable floating drawdown epsilon (default 1e-9) used uniformly in EquityBar validation instead of an inline literal.
- **FR-007**: System MUST implement (or explicitly defer with returned structured warning) walk-forward optimization grid execution; warnings are surfaced in API payload under `advanced.warnings`.
- **FR-008**: System MUST centralize metrics/equity hashing into a single function set (`hashes.metrics_signature`, `hashes.equity_signature`) and deprecate legacy duplicates.
- **FR-009**: System MUST provide migration tooling to rewrite historical records (if needed) to new model naming with backward-compatible read alias layer (no data loss).
- **FR-010**: System MUST update API and frontend schema docs to reflect unified nomenclature (Fill / CompletedTrade / EquityBar) and new validation caution output.
- **FR-011**: System MUST add integration tests asserting identical output hashes before vs after refactor (except where semantics intentionally changed and documented).
- **FR-012**: System MUST store validation gating decision and triggering p-values in the Validation table or associated artifact for audit.
- **FR-013**: System MUST add explicit run flag `optimization_mode` in results when optimization attempted (success/disabled/deferred).
- **FR-014**: System MUST enforce a maximum optimization combination count (configurable, default 250) with deterministic ordering & early abort if exceeded.
- **FR-015**: System MUST version the new unified trade schema (e.g., `trade_model_version = 2`) and include in run manifest for future migrations.

### Cross-Project Boundary
Brain (backend): Data model unification, metrics consolidation, hashing, validation gating logic, optimization execution or explicit warning emission.
Mind (frontend): Presentation updates (schema names, caution flag badge, optimization status display). Mind MUST NOT implement business logic to derive caution; it only renders provided flags.

### Key Entities
- **Fill**: Atomic execution adjustment to position (fields: ts, symbol, side, quantity, price, fees, slippage, run_id, strategy_id).
- **CompletedTrade**: Aggregated round‑trip (entry_ts, exit_ts, side, qty, entry_price, exit_price, pnl, return_pct, holding_period_bars).
- **EquityBar**: Standardized portfolio state (ts, nav, peak_nav, drawdown, gross_exposure, net_exposure, trade_count_cum).
- **MetricsSummary**: Aggregated statistics (sharpe, max_drawdown, trade_count, win_rate, exposure_pct, turnover, etc.).
- **ValidationResult**: Metric-level validation with p_value and caution evaluation.
- **OptimizationPlan (optional)**: Derived list of parameter combinations; may produce early warning if unsupported.

---

## Review & Acceptance Checklist
*GATE: To be verified prior to merging feature branch*

### Content Quality
- [ ] No implementation details leak beyond necessary module naming for boundary clarity
- [ ] Focused on user & maintainability value
- [ ] Stakeholder-readable nomenclature
- [ ] All mandatory sections completed

### Requirement Completeness
- [ ] No [NEEDS CLARIFICATION] markers remain
- [ ] All FRs testable & mapped to acceptance scenarios
- [ ] Hashing & determinism changes documented
- [ ] Scope boundaries Brain vs Mind explicit
- [ ] Migration & backward compatibility addressed
- [ ] Optimization behavior (exec vs defer) clearly defined

---

## Execution Status
*Will be updated during implementation planning*

- [ ] User description parsed
- [x] Key concepts extracted
- [ ] Ambiguities marked (none outstanding at draft stage)
- [x] User scenarios defined
- [x] Requirements generated
- [x] Entities identified
- [ ] Review checklist passed

---

## Clarifications

### Session 1 (Open Questions)
1. Trade Model Version Hashing: Should `TRADE_MODEL_VERSION` influence run hash/signature or remain metadata-only? (Impacts reproducibility baselines.)
2. Historical Equity Migration: Recompute legacy equity curves removing 1_000_000 scaling or maintain compatibility layer? Preferred rollout path?
3. Walk-Forward Optimization Scope: Implement real grid execution now or defer with structured warning? (If yes: confirm max combinations default = 250.)
4. Metrics Key Stability: Keep all existing metric key strings verbatim or allow renames for consistency?
5. Validation Caution Effect: Beyond payload flag—should caution runs be excluded from retention promotion automatically?
6. Drawdown Epsilon Config Surface: Environment variable, central settings file, or RunConfig-level override?
7. API + Frontend Deployment Strategy: Atomic merge vs feature-flagged backend first?
8. Migration Script Output Format: JSON artifact, stdout table, both?
9. Feature Flags Lifecycle: Temporary (removed post-migration) or permanent safety toggles?
10. Performance Budget Confirmation: Accept <5% median runtime regression at 10k bars? Different target?

Pending responses; planning script should pause or mark uncertainties if unanswered.

### Session 2 (Decisions)
1. Trade Model Version Hashing: EXCLUDE from run hash; metadata-only manifest field to preserve historical hash baselines.
2. Historical Equity Migration: Do NOT recompute legacy equity now; provide compatibility reader + optional recompute flag for future batch migration.
3. Walk-Forward Optimization Scope: Defer actual grid execution; emit structured warning with enumerated combination count; max combinations default 250 (configurable).
4. Metrics Key Stability: Preserve existing key names; append new names only (no renames) for backward compatibility.
5. Validation Caution Effect: Caution runs excluded from retention promotion automatically (soft policy) but data persisted normally.
6. Drawdown Epsilon Config Surface: Global setting in `settings/determinism.py` with env override `AF_DRAWDOWN_EPSILON`; no RunConfig field.
7. Deployment Sequencing: Backend ships first behind feature flags; frontend toggles after verification; flags removed within two release cycles.
8. Migration Script Output Format: Both stdout table & JSON report at `artifacts/migration/unified_trades_report.json`.
9. Feature Flags Lifecycle: Temporary; removed post-stabilization (>95% adoption) except potential emergency hashing kill-switch.
10. Performance Budget: Hard cap <5% median runtime regression (10k bars, 5-run median); early alert at ≥3% degradation.

---

## Implementation Mapping (Planning Addendum)

| FR | Scope Summary | Primary Code Touch-Points | New/Refactored Modules | Migration Needed | Notes |
|----|---------------|---------------------------|------------------------|------------------|-------|
| FR-001 | Define canonical abstractions | `models/trade.py` (rename/clarify), `domain/execution/state.py`, `services/execution.py`, `infra/orm/models.py` | `models/fill.py` (if split), `models/completed_trade.py` | Yes (schema rename or alias) | Introduce explicit naming; adapter layer for legacy tests. |
| FR-002 | Remove duplicate ad-hoc Trade dataclasses | `domain/execution/state.py`, `services/execution.py`, tests referencing internal Trade | N/A (consolidation) | Yes (update tests) | Replace internal dataclass with CompletedTrade model. |
| FR-003 | Deterministic equity normalization (remove 1e6 scaling) | `services/equity.py`, `domain/metrics/calculator.py`, `services/metrics.py` | `services/equity_normalizer.py` | Potential backfill recalculation for historical runs (optional) | Provide feature flag to compare old vs new before cutover. |
| FR-004 | Validation caution gating surfaced | `domain/validation/runner.py`, `api/routes/v1_backtests.py`, ORM Validation table | `services/validation_gating.py` | No (add columns?) | Add payload field `validation_caution` + triggering metrics list. |
| FR-005 | Metrics consolidation single entrypoint | `services/metrics.py`, `domain/metrics/calculator.py`, `services/metrics_hash.py` | `services/metrics_core.py` | No | Deprecate duplicate paths, re-export stable API. |
| FR-006 | Configurable drawdown epsilon | `models/equity_bar.py`, settings/config module | Add `settings/determinism.py` | No | Replace hard-coded 1e-9 with setting & test parameterization. |
| FR-007 | Walk-forward optimization execution or structured defer | `domain/run/orchestrator.py`, `models/walk_forward_config.py` | `services/walkforward_opt.py` | No | Emit `advanced.warnings` if unsupported; optional grid executor. |
| FR-008 | Centralize metrics/equity hashing | `services/metrics_hash.py`, callers across pipeline | Merge into `services/hashes.py` | No | Provide deprecated shim functions raising warning. |
| FR-009 | Migration tooling for model naming | `scripts/` migration script, ORM models | `scripts/migrations/unify_trades.py` | Yes | Idempotent; dry-run + report. |
| FR-010 | API/Frontend schema update | `api/routes/v1_backtests.py`, `openapi.json`, frontend TS interfaces | Update TS types (`alphaforge-mind/src/types/*`) | No | Coordinate PR across both repos/roots. |
| FR-011 | Hash regression assurance tests | `tests/determinism/` new suite | `tests/determinism/test_trade_model_unification.py` | No | Snapshot previous hash set before refactor (golden file). |
| FR-012 | Persist validation gating decision | ORM Validation model & repository | Add column `caution_flag` | Yes (schema migration) | Backfill from p_value vs threshold if reproducible. |
| FR-013 | Run optimization_mode flag | `api/routes/v1_backtests.py`, orchestrator result assembly | None (field add) | No | Values: `"success" | "disabled" | "deferred"`. |
| FR-014 | Optimization combination guard | `services/walkforward_opt.py` | None | No | Raises deterministic error with count metadata. |
| FR-015 | Trade model version in manifest | `infra/persistence.py`, run manifest builder | Add constant `TRADE_MODEL_VERSION = 2` | No | Included in hashing? (Consider excluding to avoid legacy invalidation). |

### Additional Cross-Cutting Items
- Update documentation (`README.md` determinism + data model sections).
- Add changelog entries (Pending section) summarizing schema & hashing changes.
- Provide feature flags (ENV vars) for staged rollout: `AF_UNIFIED_TRADES=1`, `AF_EQUITY_NORMALIZER_V2=1`.

---

## Test Plan Matrix

| FR | Unit Tests | Integration Tests | Contract/API | Determinism | Migration | Performance | Frontend | Notes |
|----|-----------|------------------|--------------|-------------|-----------|-------------|----------|-------|
| 001 | Model creation constraints | End-to-end run producing fills/trades | OpenAPI schema naming | Hash of sample run unchanged (except model version) | Rename script dry-run | N/A | TS types compile | Ensure no shadow classes remain. |
| 002 | Removal adapters raise if used | Pipeline using unified models | N/A | Hash parity (pre/post) | Test legacy alias import path | N/A | N/A | Deprecation warnings captured. |
| 003 | Equity normalizer math & rounding | Full backtest comparing old vs new (flagged) | API returns expected nav scale | New vs old equity hash comparison documented | Optional recalculation script | Benchmark nav build time | UI renders unchanged curve scale | Dual-run differential threshold < 1e-9 per bar. |
| 004 | Caution flag logic boundaries | Run with synthetic p_value below threshold | Payload includes `validation_caution` | Hash unaffected except validation section | N/A | N/A | Badge rendered conditionally | Include multi-metric triggers. |
| 005 | Metrics core calculations | End-to-end metrics vs legacy suite (golden) | API metrics unchanged | Metrics hash stable | N/A | Compare runtime (baseline) | TS metrics types unchanged | Remove legacy module after parity. |
| 006 | Epsilon setting override | EquityBar creation with borderline drawdown | N/A | Hash stable | N/A | N/A | N/A | Parametrized tests for epsilon. |
| 007 | Optimization planner selection | Walk-forward run with grid | Payload warnings or success plan | Run hash deterministic with plan | N/A | Guard large grids runtime | UI shows optimization_mode | If deferred, consistent warning text. |
| 008 | Unified hashing functions | End-to-end run referencing new API | Payload only new hash fields | Hash values reproducible | N/A | N/A | UI consumes unchanged field names | Deprecation warnings covered. |
| 009 | Migration name transform | Post-migration schema integration test | N/A | Hash stable (structure only) | Migration script test | N/A | N/A | Dry-run diff file produced. |
| 010 | Schema reflect new names | E2E backtest API snapshot | OpenAPI diff test | Hash unaffected | N/A | N/A | TS compile & unit tests | Use contract fixtures. |
| 011 | Hash regression harness | Pipeline deterministic multi-run | N/A | Multi-run hash identical | N/A | N/A | N/A | Introduce flake detector (repeat 5x). |
| 012 | Validation record persistence | Run with caution trigger | API exposes caution list | Hash unaffected | Data migration p_value recalculation | N/A | UI caution badge state | Include audit log entry. |
| 013 | optimization_mode flag set | Walk-forward run with and without grid | Payload field values | Hash unaffected | N/A | N/A | UI mode display | Enum coverage. |
| 014 | Combination guard triggers | Synthetic large grid | Error contract test | Hash unaffected | N/A | Guard performance (fast abort) | UI error toast | Deterministic ordering in message. |
| 015 | Manifest includes version | Run manifest build | API manifest endpoint if any | Hash policy decided (exclude?) | N/A | N/A | N/A | Add test asserting presence. |

### Determinism Strategy
- Snapshot baseline run artifacts pre-refactor (commit fixture).
- After each FR cluster (001-002, 003, 005+008, remainder) run hash comparison suite.
- Introduce `tests/determinism/regression_matrix.json` updated only by deliberate action.

### Migration Validation
- Dry-run migration prints before/after counts and field rename diff.
- Idempotency test: applying migration twice produces no changes (hash of DB unchanged second pass).

### Performance Guardrails
- Equity normalization and consolidated metrics must not increase runtime >5% (median over 5 runs 10k bars). Add micro-benchmark script.

---

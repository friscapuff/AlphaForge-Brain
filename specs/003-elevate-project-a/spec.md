# Feature Specification: Elevate Project A to Truthful Backtest Simulator (Truthful Run Foundation)

**Feature Branch**: `003-elevate-project-a`  
**Created**: 2025-09-22  
**Status**: In Implementation (Post-services revision; Type Hygiene Gate COMPLETE)  
**Input**: User description: "Elevate Project A from framework to truthful simulator by implementing an end-to-end backtest loop that consumes the 5-year NVDA CSV and produces reproducible, realism-aware results. The system must load and validate NVDA data (UTC index, exchange calendar alignment, gap/duplicate checks) and record a dataset checksum so every run is tied to a specific, immutable input. Indicators should be computed through a registry with an optional global +1 bar shift for backtests to guarantee causality, while strategies declare their required features and emit signals based only on information available at time t; positions must be applied at t+1 with a controllable fill policy (open/next-tick). We will add a minimal but honest execution simulator with spread, commission, and borrow cost models, a consistent rounding/lot policy, and a trade ledger that reconciles prices, trades, and costs into bar-level PnL. The engine should output artifact sets per run (summary.json, metrics.json, validation.json placeholder, equity.parquet, trades.parquet, plots.png, manifest.json with config hash, dataset SHA-256, calendar_id, tz, library versions, seeds) to guarantee determinism and future replay. A first validation sentinel—an in-sample permutation test with a configurable number of shuffles—must produce an empirical p-value so we can differentiate luck from structure before we invest more time; walk-forward can follow in the next iteration. Finally, expose a no-code run path through stable API contracts (POST /runs with idempotency, GET /runs/{id}, SSE /runs/{id}/events with heartbeats and milestones), enabling the future UI to stream progress, fetch artifacts, and visualize signals and equity without touching code. The outcome is a staging-quality backend where pressing “run” on NVDA yields reproducible, cost-aware results and a clear statistical sanity check, making subsequent feature/strategy additions safe and boring."

## Execution Flow (main)
```
1. Parse user description from Input
	→ If empty: ERROR "No feature description provided"
2. Extract key concepts from description
	→ Identify: actors (system, strategy developer, future UI user), actions (submit run, compute indicators, generate signals, simulate fills, produce artifacts, run permutation test), data (NVDA 5-year OHLCV, indicators, signals, trades, equity curve, metrics, manifests), constraints (determinism, causality, cost modeling, idempotent API)
3. For each unclear aspect:
	→ Mark with [NEEDS CLARIFICATION: specific question]
4. Fill User Scenarios & Testing section
	→ If no clear user flow: ERROR "Cannot determine user scenarios"
5. Generate Functional Requirements
	→ Each requirement must be testable
	→ Mark ambiguous requirements
6. Identify Key Entities (data & artifacts)
7. Run Review Checklist
	→ If any [NEEDS CLARIFICATION]: WARN "Spec has uncertainties"
	→ If implementation details found beyond WHAT/WHY: WARN to refine
8. Return: SUCCESS (spec ready for planning)
```

---

## ⚡ Quick Guidelines
- ✅ Focus on WHAT users need and WHY
- ❌ Avoid HOW to implement (no specific library design internals here)
- 👥 Written for product & quantitative stakeholders

### Section Requirements
All mandatory sections filled; optional ones kept only when relevant.

### Ambiguity Handling
All uncertainties explicitly marked. None will proceed to build without resolution.

---

## User Scenarios & Testing *(mandatory)*

### Primary User Story
As a strategy stakeholder (non-engineer UI user), I want to press “Run” for the NVDA 5-year dataset and receive a reproducible, causality-respecting, cost-adjusted backtest with statistical validation so I can trust that any reported performance is not due to data leakage or random luck.

### Acceptance Scenarios
1. **Given** a valid NVDA 5-year CSV is registered (per Spec 002 ingestion guarantees), **When** a run is submitted via POST /runs, **Then** the system creates a run record, streams progress events (data_validation → feature_build → strategy_signals → risk_sizing → execution → metrics → validation → finalized) and produces the artifact set (manifest, metrics, trades, equity, validation merge) with deterministic identifiers.
2. **Given** the same canonical RunConfig (after dataset snapshot binding) is re-submitted with identical content, **When** POST /runs is called with or without an Idempotency-Key, **Then** the existing run hash is returned and artifacts are reused (no recomputation) per Constitution Principle 1 (Deterministic Reproducibility).
3. **Given** the dataset contains duplicated timestamps, **When** validation executes, **Then** ingestion normalization (Spec 002 FR-004) resolves them and validation summary reflects `duplicates_dropped`; run does not abort unless core integrity fails (e.g., unsortable timestamps), aligning with Data Integrity principle.
4. **Given** a strategy emits a signal at bar t, **When** execution processes fills, **Then** fills occur at bar t+1 (open or configured fill policy) never at t, ensuring causality (global +1 shift already enforced for indicators in existing architecture).
5. **Given** execution costs (slippage_bps, fee_bps, optional extended slippage model, borrow_cost_bps) are configured, **When** trades are simulated, **Then** each ledger entry contains direction, quantity, execution price post slippage/fees, and cost components reconcilable to equity changes (auditability per Principle 6).
6. **Given** a validation configuration enabling permutation with N trials, **When** validation runs, **Then** metrics & validation artifacts include observed statistic, distribution summary, and p-value; if skipped (N absent / 0) placeholders appear.
7. **Given** an internal failure after partial artifact creation, **When** GET /runs/{hash} is requested, **Then** status indicates failure phase and completed artifacts remain accessible (no silent deletion) preserving provenance.

### Edge Cases
- Empty dataset slice (post date filtering) → run rejected before orchestration.
- Non-UTC internal timestamps (should not occur; ingestion normalizes) → defensive validation error.
- Unexpected market gaps (non-holiday) → recorded in validation summary; no auto-imputation.
- Strategy outputs NaN signals → bars ignored; count surfaced in metrics (FR-027).
- All permutation shuffles outperform original → high p-value caution flag present in summary.
- Borrow cost configured without short positions → borrow component zeroed (explicit not omitted).

### Explicit Out-of-Scope (Truthful Baseline)
- Partial / capacity-constrained fills (always assume full fill of target size after lot rounding).
- Residual order queues, VWAP slicing, market impact curves.
- Multi-asset portfolio aggregation (retained for a later phase).

## Requirements *(mandatory)*

### Functional Requirements
# Alignment Note: Some foundational capabilities (dataset ingestion, indicator shift, multi validation methods, basic slippage) EXIST already (see README sections 1, 4, 5, 7; Changelog 0.2.x / 0.3.0). Requirements below focus on ensuring "truthful simulator" qualities are explicit, closing remaining realism & reproducibility gaps without re-specifying delivered features.
- **FR-001**: System MUST (continue to) load the NVDA dataset via existing data source registry and compute/store dataset content hash (data_hash) in manifest (binding already present; reinforce requirement scope for truthful baseline).
- **FR-002**: System MUST validate dataset: UTC timezone, strictly increasing index, no duplicates, alignment to selected exchange calendar (calendar_id recorded), and detect gaps (classify holiday vs unexpected).
- **FR-003**: System MUST persist a validation.json (or validation merged artifact segment) summarizing structural checks regardless of success state (non-blocking anomalies captured) extending existing validation summary persistence.
- **FR-004**: System MUST maintain a feature (indicator) registry where strategies declare required features by name; only those are materialized for a run.
- **FR-005**: System MUST support an optional global +1 bar shift for all indicator-derived features when mode=backtest to enforce causality.
- **FR-006**: System MUST ensure strategy signal generation at bar t only accesses data ≤ t (post-shift) with automated runtime guard rails (future index access blocked). Guard operates in STRICT mode by default (raise on violation) with an opt-in PERMISSIVE debug mode (log + count) (see ISSUE-GUARD-001).
- **FR-007**: System MUST apply position changes no earlier than bar t+1 using a configurable fill policy: (a) next bar open, (b) next available price tick surrogate.
- **FR-008**: System MUST simulate execution costs: (a) extended slippage model (spread_pct | participation_rate), (b) bps slippage, (c) fee_bps, (d) borrow_cost_bps on short exposure accrual per bar; ordering: model adjustment → bps/fees (matches current simulator ordering comment) to preserve auditability.
- **FR-009**: System MUST enforce a portfolio rounding/lot policy (e.g., share integer, min lot=1) before booking trades.
- **FR-010**: System MUST generate a trade ledger capturing: timestamp, side, quantity, pre-cost price, post-cost execution price, fill policy, slippage model id (if any), bps slippage, fee_bps, borrow accrued (if position < 0), and resulting position & cash.
- **FR-011**: System MUST reconcile ledger entries into bar-level PnL components: realized, unrealized, cost drag; output equity.parquet.
- **FR-012**: System MUST compute metrics including (at minimum): cumulative return, volatility, max drawdown, Sharpe-like ratio, trade count, win rate, exposure %, turnover; all deterministic pure functions.
- **FR-013**: System MUST produce summary.json including human-readable outcome: runtime, bars processed, trades, final equity, p-value (if available), any caution flags (e.g., high p-value, validation warnings count).
- **FR-014**: System MUST produce plots.png artifact (equity curve + drawdown subplot) for every successful run (deterministic rendering). Rationale: immediate human validation & anomaly spotting (gaps, path dependency) without opening a notebook; low overhead relative to value. Determinism ensured via fixed matplotlib style, fixed random seeds (if any), and float formatting policy (FR-041).
- **FR-015**: System MUST output manifest.json capturing: run_id, config hash (deterministic hash over full run configuration), dataset checksum, calendar_id, timezone, feature registry version, library versions, random seeds, created_at, idempotency_key (if provided).
- **FR-016**: System MUST ensure POST /runs remains idempotent via canonical run hash and optional Idempotency-Key header (existing behavior reaffirmed; hash is primary idempotency mechanism).
- **FR-017**: System MUST implement GET /runs/{id} returning run status, artifact index (list + hash + size), and summary subset for quick UI rendering.
- **FR-018**: System MUST provide both flush and streaming SSE endpoints (already present) with heartbeat ≤15s and final terminal event; requirement clarifies acceptable heartbeat window.
- **FR-019**: System MUST record deterministic seeds governing any randomness (e.g., permutation shuffles) and ensure reruns reproduce identical permutations for same seed & config.
- **FR-020**: System MUST perform an in-sample permutation test (existing) with configurable trials (N) storing observed statistic, distribution, p_value inside validation & metrics outputs.
- **FR-020a**: System MUST surface permutation observed statistic & p_value inline in summary snapshot / events stream (real-time UI display) once permutation test completes (decision confirmed).
- **FR-021**: System MUST flag runs where p-value > configurable threshold (e.g., 0.10) with a caution indicator in summary.json.
- **FR-022**: System MUST allow runs to proceed without permutation test when parameter N=0 (skip) while still recording placeholder fields.
- **FR-023**: System MUST ensure artifact set is written to a dedicated run directory and each file hashed (SHA-256) with values in manifest.json.
- **FR-024**: System MUST allow deterministic replay: manifest + version + dataset copy produce identical run hash & identical artifact hashes using float serialization policy (precision 8, fixed) defined in FR-041 (previous clarification resolved; see Clarification #4).
- **FR-025**: System SHOULD provide run cancellation endpoint returning partial artifacts (DEFERRED: not required for first truthful baseline). Rename to SHOULD.
- **FR-026**: System MUST expose internal progress phase ordering: data_validation → feature_build → signals → execution → metrics → permutation_test → finalize.
- **FR-027**: System MUST log and surface count of ignored signals (NaN, invalid) in metrics.json.
- **FR-028**: System MUST prevent look-ahead bias by enforcing indicator shifts uniformly when global causality shift is enabled.
- **FR-029**: System MUST store config used (strategy parameters, feature params, cost model params) inside manifest.json for audit.
- **FR-030**: System MUST produce validation.json even on success (contains warnings & statistics: bar_count, first_ts, last_ts, gap_count, duplicate_count=0, holiday_gap_count, unexpected_gap_count).
- **FR-031**: System MUST update OpenAPI contract enumerating endpoints (POST /runs, GET /runs/{hash}, events flush & stream) with version set to runtime package version (Principle 9). Future divergence & media-type negotiation tracked in ISSUE-API-VERS-001 (Phase 1 policy enforced now).
- **FR-032**: System MUST ensure SSE stream terminates cleanly with a final status event (success/failure) so UI knows to stop listening.
- **FR-033**: System MUST ensure any concurrency (async orchestrator or future parallel validation) preserves deterministic event ordering & seed derivation sequence.
- **FR-034**: System SHOULD expose validation merged artifact (already implemented) consolidating multiple validation methods; permutation may be only enabled initially.
- **FR-035**: System MUST record chain_prev manifest link continuing artifact lineage (already existing; included for completeness under truthful simulator umbrella).
- **FR-036**: System MUST surface anomaly counters subset in summary snapshot event when requested (include_anomalies=true) to speed UI introspection (decision confirmed).
- **FR-037**: System MUST enforce no new nondeterministic randomness sources (e.g., numpy RNG without seed) in strategy, validation, or execution modules.
- **FR-038**: System SHOULD emit structured warning events for ignored signals and cost model anomalies (e.g., zero volume) before final metrics.
 - **FR-039**: System MUST apply borrow cost using a per-bar accrual consistent with financial best practice: `borrow_cost = |position_t| * price_t * (borrow_cost_bps / 10_000) * (bar_duration_days)` where `bar_duration_days` = 1 for daily data or (minutes_in_bar / (60*24)) for intraday; cost deducted from cash and logged in ledger (decision 9).
 - **FR-040**: System MUST allow parallel permutation trial execution while preserving determinism by: precomputing an ordered list of sub-seeds (base_seed + trial_index), executing trials in any parallel order, then sorting distribution by trial_index before hashing/artifact write (decision 7 allowed).
 - **FR-041**: System MUST fix float serialization determinism via numpy/pandas settings: `np.set_printoptions(precision=8, floatmode="fixed", suppress=True)` and DataFrame output using `float_format="%.8f"`; this policy documented in manifest (decision 4).
 - **FR-042**: System MUST implement a permutation shuffling engine that preserves structural dataset properties: (a) retains original timestamp sequence length; (b) preserves gap positions (do not create or remove gaps); (c) applies value shuffling only over return/relative transformations to avoid leaking absolute future scale; (d) validates post-shuffle integrity (no NaNs introduced). Distribution reproducibility governed by FR-019.
 - **FR-043**: System MUST output empirical significance metrics alongside traditional performance metrics: `p_value`, `trial_count`, `observed_statistic`, and `extreme_tail_ratio` (proportion of shuffled statistics exceeding observed) in both validation.json and metrics.json (extending FR-020 output) for downstream risk review.
 - **FR-044**: System SHOULD support scalable permutation execution (≥1,000 trials) with a pluggable execution backend interface (local sequential, local parallel). Determinism requirement: any backend choice yields identical ordered distribution after sorting by trial_index (FR-040). Future distributed backends tracked via ISSUE-DIST-PERM-001 (deferred).
 - **FR-045**: System SHOULD record strategy registry metadata per run: strategy_id, parameter hash, acceptance_reason (string), rejection_reason (nullable), and decision_timestamp to mitigate “strategy graveyard bias.” If provided, these fields appear in manifest and summary.json. Formal multi-strategy evaluation & registry governance deferred under ISSUE-STRAT-REG-001.
 - **FR-046**: System MUST provide walk-forward validation infrastructure: sequential rolling splits of historical data into in-sample (training) and immediately following out-of-sample (testing) windows, optimizing parameters only on the in-sample segment and applying them unchanged on the out-of-sample segment. Each segment’s metrics (in/out) plus aggregated walk-forward metrics MUST be written to validation.json and summary.json (segmented). Determinism: split boundaries derived solely from dataset length, configured window/step, and seed-free logic.
 - **FR-047**: System MUST embed hypothesis testing outputs (permutation p_value, extreme_tail_ratio) and walk-forward robustness indicators into reports alongside classical metrics (Sharpe, CAGR, max drawdown). Robustness indicators include: (a) proportion_of_profitable_oos_segments, (b) oos_consistency_score (e.g., coefficient of variation of oos returns), (c) stability_flag if any segment Sharpe deviates > configured threshold from aggregate. These appear in metrics.json and summary.json.
 - **FR-048**: System MUST enforce bias-preventive sequential splitting for walk-forward: strictly time-ordered segments, no peeking beyond each in-sample end when optimizing, no reuse of future data in earlier folds. Validation MUST assert segment boundaries are monotonic and non-overlapping (except optional configured warm-up overlap). Violations cause run failure.
 - **FR-049**: System SHOULD define future adaptive validation placeholders (bootstrap resampling, Monte Carlo path perturbations, regime stress tests, meta-validation across strategies) documented in validation.json under a `future_methods` section listing inactive methods for transparency (non-executable in this release).

### Key Entities (Refined)
- **Dataset**: Canonical NVDA OHLCV time series (UTC, validated) + data_hash (Spec 002).
- **Feature Registry**: Declarative list of available indicators (name, required inputs, shiftable flag, version tag).
- **Strategy Definition**: Declares required features, parameter block, signal function contract.
- **Signal Series**: Time-aligned vector of intended position changes or target weights (pre-fill).
- **Execution Policy**: Fill timing (open/next-tick), lot sizing rules.
- **Cost Model**: Parameters for spread, commission, borrow; calculation rules.
- **Trade Ledger**: Ordered record of executed trades with cost components and resulting state.
- **PnL / Equity Curve**: Aggregated portfolio value series with component attribution.
- **Run Manifest**: Deterministic metadata enabling replay & audit.
- **Metrics Set**: Derived performance/statistics (returns, risk, quality, p-value).
- **Events Stream**: Milestone + heartbeat events for UI consumption.
- **Validation Result**: Aggregated permutation (and future block_bootstrap, monte_carlo_slippage, walk_forward) with distributions & p-values.

---

## Review & Acceptance Checklist

### Content Quality
- [x] No low-level implementation details (focus on WHAT & data contracts)
- [x] Focused on user & analytical value
- [x] Accessible to non-implementers
- [x] All mandatory sections completed

### Requirement Completeness
- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements testable & structured
- [x] Success criteria measurable (determinism, artifact hashes, p-value)
- [x] Scope bounded to initial truthful simulator foundation
- [x] Dependencies & assumptions identified implicitly (dataset availability, exchange calendar source)
- [x] Type Hygiene Gate (T080–T086) complete (zero mypy errors; no unused ignores) BEFORE API layer work (FR-017..FR-018 exposure)

---

## Execution Status
- [x] User description parsed
- [x] Key concepts extracted
- [x] Ambiguities marked
- [x] User scenarios defined
- [x] Requirements generated
- [x] Entities identified
- [x] Review checklist passed
> Update 2025-09-22: Service layer tasks (T034–T049) implemented. Type Hygiene Gate achieved (T080–T086). API & persistence phases UNBLOCKED (dependency order still enforced). CI typing gate active.

---

### Clarifications Status & Explanations
| # | Topic | Status | Decision / Explanation |
|---|-------|--------|------------------------|
| 1 | Capacity / Partial Fills | RESOLVED (Deferred) | Out of scope; always full-fill after lot rounding. Future issue: CAP-001 will introduce participation & residual modeling. |
| 2 | Future Data Access Guard | RESOLVED (Strict Default) | ISSUE-GUARD-001 created. Decision: runtime `CausalContext` guard with STRICT default (raise + abort strategy evaluation on first violation) and optional PERMISSIVE debug mode (log + increment counter) behind config flag. Implementation Steps: (1) Proxy accessors restricting window; (2) Unit tests with intentional violations; (3) Metrics field `future_access_violations`; (4) Integration test asserts zero violations for baseline strategies; (5) Documentation section in README "Causality Enforcement". Static analysis deferred (complexity > value). |
| 3 | Plot Artifact Mandate | RESOLVED | Chosen MUST: FR-014 updated. Determinism plan: enforce fixed matplotlib rcParams (font, backend 'Agg', style seed), disable interactive randomness, use consistent figure size & dpi; hash stability verified in test by regenerating on identical run. |
| 4 | Float Determinism Policy | RESOLVED | Adopt numpy print options (precision=8, floatmode=fixed, suppress=True) + pandas float_format="%.8f"; parquet written with consistent dtype; manifest records `float_precision: 8`. |
| 5 | Run Cancellation Endpoint | DEFERRED (Issue Logged) | ISSUE-CANCEL-001 created. Decision: Defer implementation until async orchestration + multi-run manager exist. Rationale: Avoid half-implemented cancellation semantics & race conditions. FR-025 remains SHOULD; removal or escalation contingent on orchestrator maturity milestone. |
| 6 | API Versioning Strategy | PHASE 1 CONFIRMED | ISSUE-API-VERS-001 created. Phase 1: OpenAPI info.version == package version; no separate header. Future triggers for Phase 2 (preview header) logged: (a) introduction of optional experimental endpoint; (b) need for client capability negotiation. Phase 3 (media-type versioning) only if unavoidable breaking change. README & OpenAPI to document version semantics + additive change policy. |
| 7 | Parallel Permutation Trials | RESOLVED | Allowed with deterministic seeding (base_seed + i) and ordering results by index pre-hash (FR-040). |
| 8 | Snapshot p-value & Anomalies | RESOLVED | Required; FR-020a, FR-036 escalated to MUST. SSE emits updated summary event upon permutation completion. |
| 9 | Borrow Cost Accrual Formula | RESOLVED | Per-bar accrual: notional * (bps/10_000) * bar_duration_days; intraday uses minutes_in_bar/1440 (FR-039). |
| 10 | Pre-API Type Hygiene Gate | RESOLVED (Adopted) | Insert Phase 3.4H between services and API. Scope: T080 conftest path fix, T081 remove unused ignores, T082 test annotations, T083 service annotation tightening, T084 external stub/ignore decision, T085 CI zero-error gate, T086 cross-link updates. Gate: zero mypy errors & no unjustified ignores before starting API endpoints. Rationale: prevent type debt from leaking into public contracts; strengthen determinism & replay guarantees. |

### Remaining Open Items
None (all prior open clarifications now tracked via inline issues below). Type Hygiene Gate is an adopted decision (see DECISION block) not an unresolved clarification.

### Inline Issue Stubs
#### ISSUE-GUARD-001: Runtime Future Data Access Guard Implementation
Status: OPEN
Owner: Simulation Subsystem Lead
Summary: Implement STRICT default causality guard (FR-006) with PERMISSIVE debug mode. Provide metrics, tests, and README documentation.
Acceptance:
 - All baseline strategies produce zero violations.
 - Intentional violation test raises deterministically in STRICT mode.
 - Metrics field `future_access_violations` appears (0 for baseline) in metrics.json.
 - Performance overhead <1% on 1M-bar synthetic benchmark (document measurement).

#### ISSUE-CANCEL-001: Run Cancellation Endpoint Defer
Status: DEFERRED
Owner: Orchestration Lead
Summary: Evaluate and implement POST /runs/{id}/cancel once async multi-run orchestration exists.
Prerequisites: Run state machine with interruptible phases; artifact finalization policy; SSE cancellation event schema.
Exit Criteria: Decision to either (a) implement cancellation with test coverage (idempotent, race-safe) or (b) remove FR-025 if determined unnecessary.

#### ISSUE-API-VERS-001: API Versioning Evolution
Status: OPEN (Tracking)
Owner: Platform/API Steward
Summary: Monitor for triggers requiring Phase 2 (preview header) or Phase 3 (media-type negotiation).
Phase 2 Triggers: Experimental endpoint requiring client opt-in; need to surface preview change log.
Phase 3 Trigger: Unavoidable breaking change to existing response contract.
Deliverables: README section "API Versioning" + change log entries; optional Accept header prototype when triggered.

#### DECISION-2025-09-22-TYPE-HYGIENE-GATE
Status: IMPLEMENTING (GATE)
Summary: Enforce zero mypy errors & removal of unused ignores prior to API implementation. Codified as Phase 3.4H in `tasks.md` with tasks T080–T086.
Motivation: Strengthen determinism & correctness guarantees; prevent type-driven refactors after public contract exposure; align with Principle P10 (Tooling & Typing) and P1 (Deterministic Reproducibility).
Scope Tasks:
 - T080 tests/conftest.py path fix
 - T081 remove unused `# type: ignore`
 - T082 annotate tests & generics
 - T083 tighten service annotations
 - T084 external stub vs ignore decision (e.g., types-toml)
 - T085 CI gate & baseline typing hash update
 - T086 artifact cross-link updates (spec/plan/quickstart)
Exit Criteria:
 - mypy strict: 0 errors
 - No broad `# type: ignore` without specific code & justification
 - Updated artifacts mention gate
 - CI fails on any new mypy error
Artifacts Impacted: `spec.md`, `plan.md`, `quickstart.md`, `tasks.md`, `typing_timing.json`.

---

### Acceptance to Move to Planning
All clarifications resolved or formally deferred with issue tracking (ISSUE-GUARD-001, ISSUE-CANCEL-001, ISSUE-API-VERS-001). No [NEEDS CLARIFICATION] markers remain. Ready for implementation planning.


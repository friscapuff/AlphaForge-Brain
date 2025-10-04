# Feature Specification: AlphaForge Mind Initial Tabs (Chart Analysis & Backtest/Validation)

**Feature Branch**: `006-begin-work-on`
**Created**: 2025-09-26
**Status**: Draft
**Input**: User description: "Begin work on alphaforge mind, the frontend. For now I only want to focus on the creation of 2 tabs that i believe are essntial and paramount to success. The first tab is a candle chart analysis tab and tool that will be completely based off of lighweight charts from tradingviews complete with all its features. The second tab is a backtest and validation tab which  will contain various visualizations related to my backtest and validation; this tab should include a strategy builder in which i can define various information regarding backtest and strategy inputs such as date from to, ticker, strategy, upon selecting strategy the corresponding params appear for edit, risk management inputs. after setting these up, there should be a run test button which sends information back to the backend alphaforge brain for processing and returns results to alphaforge mind for viewing. This must contain a montecarlo walkforward graph that shows me a dynamic build of the strategy within the simulation."

## Execution Flow (main)
```
1. Parse user description from Input
	→ If empty: ERROR "No feature description provided"
2. Extract key concepts from description
	→ Identify: actors (user/trader, Mind UI, Brain backend), actions (view candles, configure strategy, run backtest, view validation & Monte Carlo), data (OHLCV, indicators, strategy params, risk settings, backtest results, walk-forward simulations), constraints (determinism, responsiveness, parameter validation)
3. For each unclear aspect:
	→ Mark with [NEEDS CLARIFICATION: specific question]
4. Fill User Scenarios & Testing section
	→ If no clear user flow: ERROR "Cannot determine user scenarios"
5. Generate Functional Requirements
	→ Each requirement must be testable
	→ Mark ambiguous requirements
6. Identify Key Entities (data involved: ChartSeries, StrategyConfig, BacktestRequest, BacktestResult, MonteCarloPath)
7. Run Review Checklist
	→ If any [NEEDS CLARIFICATION]: WARN "Spec has uncertainties"
	→ If implementation details found: ERROR "Remove tech details"
8. Return: SUCCESS (spec ready for planning)
```

---

## ⚡ Quick Guidelines
- ✅ Focus on WHAT users need and WHY
- ❌ Avoid HOW to implement (underlying framework details of charting library usage hidden unless needed for boundary definition)
- 👥 Written for business stakeholders & product
- 🧩 Dual project boundary: Brain performs computation (backtest, validation, Monte Carlo), Mind presents interactive UI & collects input.

---

## User Scenarios & Testing *(mandatory)*

### Primary User Story
As a quantitative trader using AlphaForge Mind, I want to visually explore instrument price action with interactive candlestick charts and rapidly configure and launch deterministic backtests (including Monte Carlo walk-forward analyses) so that I can iterate on strategies and evaluate robustness without leaving the unified interface.

### Acceptance Scenarios
1. Given the user opens the Chart Analysis tab, When they select a ticker and date range, Then an interactive candlestick chart with volume and default indicators loads within <2s for recent data.
2. Given the user has loaded a chart, When they add or remove built-in overlays/indicators (e.g., SMA(20), EMA(50)), Then the chart updates and state persists during session navigation.
3. Given the user navigates to the Backtest & Validation tab, When they choose a strategy from a dropdown, Then its parameter form (with defaults) and risk inputs (e.g., max position size, stop loss method) appear.
4. Given a valid configuration (dates, ticker, strategy params, risk settings), When the user clicks Run Test, Then a backtest request is sent to Brain and a pending state with progress (e.g., phases or spinner) is shown.
5. Given Brain completes processing, When results are returned, Then equity curve, trade distribution stats, validation summary (bootstrap/permutation/walk-forward), and Monte Carlo walk-forward visualization render.
6. Given multiple backtests have been run, When the user selects a previous run from a history list, Then all result visualizations update to that run’s data.
7. Given an invalid parameter (e.g., end date before start date), When user attempts Run Test, Then the system blocks submission and shows a clear inline error.

### Edge Cases
- Missing or sparse OHLCV data → Chart displays gaps or a no-data placeholder with guidance.
- Extremely long date range selection → System warns about performance and may require confirmation if span >5 years (no hard cap—proceed allowed with confirmation modal).
- Strategy with optional parameters not set → Uses documented defaults and clearly indicates which values were defaulted.
- Backtest in progress and user navigates away → Progress state resumes upon return (no data loss). Background processing continues server-side; client resumes polling when user returns.
- Monte Carlo run generates more than 200 default paths → Additional paths beyond user-adjustable cap (e.g., slider) require explicit user increase; initial default = 200 paths.
- Backend failure (timeout or validation error) → Unified error banner plus per-field hints if validation related.
- User attempts multi-ticker input (comma separated or multi-select) → Validation error: "Only one ticker per backtest in this release".

## Requirements *(mandatory)*

### Functional Requirements
- **FR-001**: Users MUST be able to open a Chart Analysis tab and load candlestick data for a selected ticker and date range.
- **FR-002**: System MUST support adding/removing common overlays & indicators (min: SMA, EMA, VWAP, Bollinger Bands, Volume) with parameter input per indicator.
- **FR-003**: Users MUST be able to configure a Backtest via form: date_from, date_to, single ticker only (multi-asset / portfolio mode explicitly out of scope for this release), strategy, strategy parameters (dynamic based on strategy), and risk management inputs (e.g., max position size, stop type, slippage model choice).
- **FR-004**: System MUST validate required fields and block submission with clear human-readable errors for invalid or inconsistent inputs.
- **FR-005**: Users MUST trigger a Run Test action that submits a structured BacktestRequest to Brain and receives an identifier for tracking.
- **FR-006**: Users MUST see progress or status for an in-flight backtest (queued, running, completed, failed).
- **FR-007**: Upon completion, System MUST display: equity curve and REQUIRED metrics set {CAGR, Max Drawdown %, Sharpe Ratio (annualized), Win Rate %, Trade Count, Profit Factor, Exposure %, Return/Risk (CAGR/MaxDD)} plus parameter echo.
- **FR-008**: System MUST display validation outputs with REQUIRED artifacts: (a) Bootstrap CIs for {CAGR, Max Drawdown, Sharpe} (fields: metric, lower, upper, confidence_level=0.95), (b) Permutation Test result (fields: test_name, p_value, iterations), (c) Walk-Forward Splits list (train_start, train_end, test_start, test_end, metrics {CAGR, MaxDD, Sharpe}). Disabled artifacts MUST show placeholder status.
- **FR-009**: System MUST render a Monte Carlo visualization that progressively reveals simulated paths in batches (default batch size 25 every ≤50ms frame) relative to realized equity curve; if redraw exceeds 300ms threshold system MAY fallback to percentile bands + sample subset.
- **FR-010**: Users MUST be able to switch between multiple completed backtest runs (history list or dropdown) and have all visualizations update accordingly.
- **FR-011**: System MUST persist the most recent configuration in local session state for rapid iteration.
- **FR-012**: System MUST handle backend error responses gracefully and surface descriptive messages (e.g., invalid parameter, data unavailable) to the user.
- **FR-013**: Strategy parameter form MUST update dynamically when strategy selection changes, resetting parameters to that strategy’s defaults.
- **FR-014**: Risk management inputs MUST include at least: position sizing limit, stop loss type, take profit toggle, and optional daily loss cap. (Additional risk controls out of scope this release.)
- **FR-015**: System MUST provide a deterministic canonical JSON export (stable key ordering) via preview modal with copy and download (.json) actions.
- **FR-016**: Users MUST be able to refresh chart data and have indicator overlays reapply without manual reconfiguration.
- **FR-017**: Monte Carlo visualization MUST allow toggling path opacity and highlight 5th & 95th percentile bands by default when bands are enabled.
- **FR-018**: System MUST display walk-forward timeline segmentation (train/test slices) alongside equity curve or as separate mini-chart.
- **FR-019**: System MUST enforce deterministic mapping between a backtest run identifier and displayed result set (no mixing of runs).
- **FR-020**: System MUST surface a "Slow response" unobtrusive notification if backend run submission to first result payload exceeds 5 seconds (one-time per run) and optionally offer background mode.
- **FR-021**: System MUST warn (confirmation required) when requested date span exceeds 5 years but allow continuation (no hard limit).
- **FR-022**: Monte Carlo simulation MUST default to 200 paths on initial render; user MAY adjust within a bounded range (min 20, max 500) before re-requesting visualization.

### Cross-Project Boundary
- Brain responsibilities: ingest OHLCV + adjustments, compute backtest results, generate trade/equity series, validation metrics, Monte Carlo simulation paths, deterministic run identifiers.
- Mind responsibilities: present charts & controls, collect and validate user inputs client-side, request computations, poll or subscribe for status, render returned datasets without altering core metrics.
- No simulation or statistical computation occurs in Mind beyond light formatting, aggregation for visualization, and client-side parameter validation.

### Key Entities
- **ChartSeries**: Temporal OHLCV + volume data used for candlestick rendering.
- **IndicatorConfig**: Name, parameters, enabled state.
- **StrategyConfig**: Strategy identifier plus parameter key-value pairs and version.
- **RiskConfig**: Position sizing rules, stop/take profit settings, limits.
- **BacktestRequest**: date_from, date_to, ticker(s), StrategyConfig, RiskConfig, validation flags.
- **BacktestRun**: Run id, status, submitted_at, completed_at, summary metrics.
- **BacktestResult**: Equity curve, trades list summary stats, validation outputs.
- **MonteCarloPath**: Sequence of (step_index, equity_value) forming one simulated path.
- **WalkForwardSplit**: Train period, test period, metrics summary for that slice.

---

## Review & Acceptance Checklist
*GATE: Automated checks run during main() execution*

### Content Quality
- [ ] No implementation details (languages, frameworks, APIs)
- [ ] Focused on user value and business needs
- [ ] Written for non-technical stakeholders
- [ ] All mandatory sections completed

### Requirement Completeness
- [ ] No [NEEDS CLARIFICATION] markers remain
- [ ] Requirements are testable and unambiguous
- [ ] Success criteria are measurable
- [ ] Scope is clearly bounded
- [ ] Dependencies and assumptions identified
- [ ] If dual project: Brain/Mind boundary defined

---

## Execution Status
*Updated by main() during processing*

- [x] User description parsed
- [x] Key concepts extracted
- [x] Ambiguities marked
- [x] User scenarios defined
- [x] Requirements generated
- [x] Entities identified
- [ ] Review checklist passed

## Clarifications
### Session 2025-09-26
- Q: Do backtests in this initial Mind release support multiple tickers, and if so, how are they treated? → A: Single ticker only (Option A)
- Q: What is the maximum permitted chart/backtest date span a user can request in this initial release? → A: No hard limit; warn >5y (Option D)
- Q: What should be the default number of Monte Carlo simulation paths displayed (before any user adjustment)? → A: 200 paths (Option D)
- Q: Which percentile bands should the Monte Carlo visualization highlight by default (when the user toggles bands on)? → A: 5th & 95th percentiles (Option A)
- Q: What latency threshold should trigger the user-facing “slow response” feedback for a backtest run? → A: >5 seconds (Option B)
- Q: Should background processing continue if tab closed? → A: YES (server continues; client resumes polling on return)

### Error Taxonomy
| Code | Category | Trigger | User Message |
|------|----------|---------|--------------|
| validation_error | 4xx | Invalid input (date range, params) | Invalid input: <field>: <reason> |
| limit_exceeded | 4xx | Monte Carlo paths <20 or >500 | Monte Carlo paths must be between 20 and 500 |
| not_found | 4xx | Unknown run_id | Run not found |
| rate_limited | 429 | Burst threshold exceeded | Too many requests, slow down |
| internal_error | 5xx | Unhandled server failure | Unexpected server error (ref: <id>) |
| data_unavailable | 424 | Missing market data | Data unavailable for selected range |
| timeout | 504 | Backend processing exceeded SLA | Processing taking longer than expected |

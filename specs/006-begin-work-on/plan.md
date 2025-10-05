# Implementation Plan: AlphaForge Mind Initial Tabs (Chart Analysis & Backtest/Validation)

**Branch**: `006-begin-work-on` | **Date**: 2025-09-26 | **Spec**: `specs/006-begin-work-on/spec.md`
**Input**: Feature specification from `/specs/006-begin-work-on/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
2. Fill Technical Context (scan for NEEDS CLARIFICATION) → All critical clarifications resolved (Session 2025-09-26)
3. Fill the Constitution Check section based on constitution v1.2.0
4. Evaluate Constitution Check (initial)
5. Execute Phase 0 → research.md (OUTCOME documented inline below for /plan scope; separate file generated in subsequent automation step if required)
6. Execute Phase 1 → design draft (data-model.md, contracts/, quickstart.md stubs referenced for /tasks phase)
7. Re-evaluate Constitution Check (post-design)
8. Plan Phase 2 approach (describe only; tasks.md generated later)
9. STOP - Ready for /tasks command
```

## Summary
Deliver two foundational AlphaForge Mind tabs:
1. Chart Analysis: High-performance candlestick + volume + overlays using TradingView lightweight-charts (LWC) with indicator management, multi-timeframe reload, responsive layout, theme support.
2. Backtest & Validation: Strategy configuration form (dynamic params + risk), run orchestration to Brain backend, progress feedback, results visualization (equity curve, metrics, trade stats, validation summaries, Monte Carlo walk-forward with percentile bands).

Focus: Deterministic contracts Brain↔Mind, minimal client computation, extensible visualization layer.

## Technical Context
**Language/Version**: TypeScript (React 18+), Node 20 toolchain, backend remains Python 3.11 (Brain)
**Primary Dependencies**: React, React Router (or file-route alt), lightweight-charts, Tailwind CSS, Zustand (lightweight global state) or Redux Toolkit (TBD), React Query (TanStack Query) for async fetch + caching, d3-array (selective) for lightweight statistical transforms (if needed for client percentile shading only)
**Storage**: Browser memory + optional localStorage for session persistence of last config
**Testing**: Vitest + React Testing Library + Playwright (e2e later). Contract tests via schema snapshots (JSON) comparing Brain responses.
**Target Platform**: Modern Chromium/Firefox/Safari (ES2022), responsive desktop-first with adaptive layout.
**Project Type**: brain+mind dual
**Performance Goals**:
- Initial candlestick render < 150ms after data payload arrival for <= 5k bars
- Backtest run submission → first status event < 5s (else slow notice FR-020)
- Monte Carlo redraw (200 paths) < 300ms on mid-range laptop (throttled 6x CPU)
- Memory footprint of charts tab < 75MB in-performance panel for default path count
**Constraints**:
- Determinism: No random client augmentation; Monte Carlo paths delivered pre-sorted from Brain with seed id.
- Latency instrumentation required for submission + result payload.
- Accessibility baseline: semantic regions + keyboard nav for form, color contrast ≥ WCAG AA for critical metrics.
**Scale/Scope**:
- Single-user interactive sessions, typical dataset: 1–5 years OHLCV daily or intraday (assume aggregated timeframe). Strategy result equity series length O(1k–20k points). Monte Carlo paths 200×N (N up to equity length).

## Constitution Check (Initial)
- Determinism: PASS (Brain supplies deterministic data; client purely renders)
- Test-First: PLAN to scaffold failing tests per FR list (mapping FR-001..022 to test files) before implementation.
- Modular MVC / Dual Root: PASS (All new code isolated under `alphaforge-mind/`; Brain untouched except contract definitions)
- Observability: PLAN instrumentation hooks: fetch wrapper logs timings, chart mount performance marks, run lifecycle spans.
- Contract Versioning: New endpoints/JSON schemas versioned under `/v1/mind/backtest` namespace; no breaking change to existing Brain public APIs (ADD only → MINOR acceptable)
- Performance Targets: Explicit above.
- Data Integrity: No schema mutation of existing Brain objects; additive response envelope for backtest results.

If any FAIL → STOP. All currently PASS with planned enforcement via tasks.

## Project Structure

### Documentation (this feature)
```
specs/006-begin-work-on/
├── plan.md
├── research.md (Phase 0 output)
├── data-model.md (Phase 1)
├── quickstart.md (Phase 1)
├── contracts/ (Phase 1)
└── tasks.md (Phase 2 via /tasks)
```

### Source Code (dual project target)
```
alphaforge-brain/
  src/
  tests/

alphaforge-mind/
  src/
    components/
      charts/
      backtest/
      common/
    pages/
      ChartAnalysisPage.tsx
      BacktestValidationPage.tsx
    state/
    services/
      api/
      adapters/
    hooks/
    styles/
    utils/
  tests/
    unit/
    integration/
    contracts/
```

**Structure Decision**: Dual Project (Brain producer, Mind consumer) – enforce contract directory for schemas.

## Phase 0: Outline & Research
Objectives:
- Validate lightweight-charts (LWC) capability coverage vs FRs.
- Define minimal API shapes for: /chart/data, /backtest/run, /backtest/status/{id}, /backtest/result/{id}, /backtest/montecarlo/{id}?paths=n
- Assess state mgmt: Keep global lean (Zustand) + query cache (React Query) vs heavier Redux.
- Evaluate alternatives for interactive overlays (custom drawing vs built-in series). Decision: Use LWC built-in series & custom price lines; postpone custom canvas layering until needed.
- Monte Carlo rendering strategies: (a) Draw each path as separate line series (expensive > ~150 paths) (b) Single canvas overlay custom rendering. Decision: Use batch overlay custom layer to reduce series churn; fallback: selective subset highlight (percentile bands + sample paths) if performance risk.
- Percentile shading: Precomputed percentile arrays from Brain; client just maps index→value.
- Accessibility & theming: Tailwind design tokens + CSS variables controlling LWC colors; dark/light toggle stored in state.
- Error surfaces: Central <ErrorBoundary/> + inline field validation.
- Progress mechanics: Polling vs SSE/WebSocket. Decision: Start with polling (simple) interval 1s escalating to 2s after 10s; add SSE later (future FR) if latency jitter emerges.

Research Notes Summary:
- LWC supports: candlestick, volume histogram, area/line overlays, price lines, markers. Lacks native multiple-y axes (workaround: offset scaling or dual chart stack). FR scope only needs single y-axis + volume separate pane (supported via separate series or stacked layout).
- For 5th/95th bands: Use area fill between percentile lines (two line series + fill) OR custom polygon; start with twin line series + setSeriesOptions({topColor,bottomColor}).

## Phase 1: Design & Contracts

### Cross-Project Contracts (initial draft)
- GET /api/v1/chart?symbol=...&from=...&to=...&interval=1D → CandlesPayload
- POST /api/v1/backtest/run → BacktestRunRequest returns {run_id}
- GET /api/v1/backtests/{run_id} → {run_id, status, submitted_at, started_at?, completed_at?}
- GET /api/v1/backtests/{run_id}/result → BacktestResultPayload (metrics, equity, trades_summary, validation, walkforward_splits)
- POST /api/v1/backtests/{run_id}/montecarlo (body: {paths, seed, extended_percentiles?}) → MonteCarloPathsPayload (paths[], percentiles{p5[],p95[]}, seed)

(Exact JSON schema to be formalized under `contracts/` with version tags `v1`.)

### Data Model (Mind-side TypeScript Interfaces - draft)
- Candle { t: epoch_ms; o:number; h:number; l:number; c:number; v:number }
- IndicatorConfig { id:string; type:'sma'|'ema'|'vwap'|'bollinger'|'volume'; params:Record<string,number>; enabled:boolean }
- StrategyParam { name:string; value:number|string|boolean; type:'number'|'int'|'enum'|'bool'; min?:number; max?:number }
- StrategyConfig { strategy_id:string; params:StrategyParam[]; version:string }
- RiskConfig { position_size_pct:number; stop_type:'percent'|'atr'|'none'; stop_value?:number; take_profit?:number; daily_loss_cap?:number }
- BacktestRunRequest { date_from:string; date_to:string; ticker:string; strategy:StrategyConfig; risk:RiskConfig; validation:{ bootstrap:boolean; permutation:boolean; walkforward:boolean; montecarlo:boolean } }
- BacktestRunStatus { run_id:string; status:'queued'|'running'|'completed'|'failed'; submitted_at:string; started_at?:string; completed_at?:string; error?:string }
- EquityPoint { t:epoch_ms; equity:number }
- MonteCarloPath { path_id:number; points:EquityPoint[] }
- MonteCarloPayload { run_id:string; seed:string; paths:MonteCarloPath[]; p5:EquityPoint[]; p95:EquityPoint[] }

### Component Architecture (High-level)
- ChartAnalysisPage
  - SymbolSelector, DateRangePicker, IndicatorManager, CandleChart (wrapper around LWC), IndicatorPanel
- BacktestValidationPage
  - StrategySelector, DynamicParamForm, RiskForm, ValidationToggles, RunButton, StatusBanner
  - ResultsPanel
    - EquityCurveChart, MetricsGrid, TradesSummaryTable, ValidationSummary, WalkForwardSplitsChart, MonteCarloChart

### State & Data Flow
- Global store (Zustand): current ticker, date range, active indicators, last backtest config, selectedRunId
- React Query: Keys: ['chart',symbol,range], ['backtest','status',run_id], ['backtest','result',run_id], ['backtest','mc',run_id,paths]
- Derived selectors for UI mapping; no business logic in components.

### Performance Considerations
- Debounce input for date range & indicator toggles (150ms) before fetch
- Memoize transformed data arrays for charts
- Offload large JSON parsing with streaming if payload >5MB (future optimization task)

### Error & Loading Strategy
- Uniform ApiClient wrapper returns Result<T,Error>
- Skeleton states for charts (placeholder candles), shimmer for metrics
- Timeout escalation: if status still queued after 30s, show gentle retry suggestion

## Phase 2: Task Planning Approach (Description Only)
Tasks will be generated grouping by:
1. Contracts: Define JSON schemas & TS types (FR-001..022 mapping)
2. Infrastructure: Mind project scaffold (React + Tailwind config, build tooling, lint, test harness)
3. Chart Analysis Implementation: Data fetcher, CandleChart wrapper, indicator overlay handling
4. Backtest Orchestration: Forms, validation, run submission + polling, status model
5. Results Visualization: Equity curve, metrics, validation, Monte Carlo (phased: base render → optimized layering → progressive reveal batches)
6. State Management & Persistence: Zustand store, session restore
7. Observability & Performance: Timing instrumentation, simple profiler marks
8. Testing: Unit (types & transforms), integration (form submit flows), contract (schema assertions), visual/regression baseline for charts (playwright screenshot diff placeholder)
9. Documentation & Quickstart: Setup instructions, dev server run, contract reference

Each task will cite FR IDs & Constitution principle mapping where relevant (Determinism, Test-First).

## Complexity Tracking
| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|---------------------------------------|
| Custom Monte Carlo overlay layer | Performance for >100 line series | Native multiple series would degrade FPS & memory |

## Progress Tracking
**Phase Status**:
- [x] Phase 0: Research complete (/plan scope)
- [x] Phase 1: Design complete (/plan scope)
- [ ] Phase 2: Task planning complete (/tasks command pending)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [x] Complexity deviations documented

## Enhancing Interactive Visuals Beyond Chart Tab
To ensure rich, consistent interactivity across the entire Mind frontend beyond candlestick charts:
1. Visualization Toolkit Layer: Create a lightweight internal wrapper library (`alphaforge-mind/src/components/viz/`) exposing standardized primitives: TimeSeriesChart, DistributionPlot, PercentileBand, MetricSparkline. Internally uses lightweight-charts for time-based series and minimal SVG (or Canvas) for non-time distributions.
2. Micro-Interactions: Utilize Tailwind + small Framer Motion subset (optional) ONLY for focus/hover transitions (not heavy animation). Keep motion disabled preference respected (prefers-reduced-motion media query).
3. Consistent Color System: Define semantic tokens (--color-equity, --color-drawdown, --color-mc-path, --color-mc-band) enabling theme switching without per-component overrides.
4. Data Density Adaptation: Automatically collapse secondary panels (e.g., Trade Distribution) when viewport < 1200px; offer expand toggles.
5. Progressive Disclosure: Default to core metrics; advanced validation panels behind accordion to reduce initial cognitive load/perf cost.
6. Accessible Tooltips: Centralized tooltip manager with keyboard navigable data points (arrow keys to move along equity series).
7. Snapshot & Share: Provide a client-side PNG export util for any time-series component (canvas to blob) plus embedded metadata (run_id, timestamp) for reproducibility.
8. Uniform Loading Skeletons: Shared Skeleton primitives keep perceived latency low.
9. Declarative Layout: Potential adoption of a layout grid component allowing rearrange (future FR) – defer until user need signaled.
10. Pluggable Renderer Path: Abstract Monte Carlo and equity rendering so future WebGL acceleration path can be added without rewriting consumers.

Rationale: This yields consistency, performance predictability, and faster future expansion (e.g., options Greeks surfaces, risk heatmaps) without premature generalization.

## Next Steps
Run /tasks to generate tasks.md with concrete, test-first actionable items aligned to FR-001..FR-022 and Constitution principles.

## Addendum (2025-09-26 Scaffold & Extensions)
- Early frontend scaffold created under `alphaforge-mind/` (React + Vite + Tailwind config files, initial pages, routing placeholder, state directories).
- Added extended percentile & validation optional fields design (data-model v0.2) supporting p1/p50/p99 future expansion and sensitivity/regime toggles.
- Introduced schema evolution via `v1alpha2` for `backtest-run-request` and `montecarlo-paths` including optional `sensitivity`, `regime`, and `extended` percentile object.
- Test matrix (pending file) will ensure FR mapping includes new optional flags (non-blocking baseline FR scope).
- No changes to originally enumerated FRs; extensions are additive and backward compatible.

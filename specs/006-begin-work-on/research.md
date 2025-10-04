# Phase 0 Research: AlphaForge Mind Initial Tabs

## Goals
Establish feasibility, library capability coverage, contract boundaries, and performance strategy for:
1. Chart Analysis (candlestick, indicators) via lightweight-charts (LWC)
2. Backtest & Validation visualization (equity, metrics, Monte Carlo, walk-forward)

## Library Capability Mapping (lightweight-charts)
| Requirement | LWC Support | Notes |
|-------------|------------|-------|
| Candlestick + Volume | Native (CandlestickSeries + HistogramSeries) | Separate volume pane achievable by stacking containers |
| Overlay Indicators (SMA/EMA) | Use LineSeries computed client-side or served pre-calculated | For determinism prefer Brain pre-compute; fallback quick calc is pure & deterministic |
| Bollinger Bands | Two LineSeries (upper/lower) + area fill OR polygon | Start with twin line fill |
| VWAP | LineSeries | Brain supplies cumulative price*volume / cumulative volume |
| Markers (entries/exits) | setMarkers | Distinguish trades (triangle up/down) |
| Percentile Bands (Monte Carlo) | Two LineSeries + fill | Precomputed percentiles from Brain |
| Multiple Path Rendering | Many LineSeries (costly) | Custom canvas overlay for >100 paths |
| Theming (dark/light) | Via overriding series & layout options | Central theme tokens |
| Resize Responsiveness | Built-in API | Debounce container resize |

## Key Trade-offs
- Monte Carlo Path Rendering: Choose custom canvas overlay for scalability beyond ~100 line series; complexity justified by performance (Complexity Tracking entry).
- State Management: Zustand + React Query vs Redux Toolkit. Chosen approach yields smaller bundle and direct entity caches; complexity of Redux not justified initially.
- Polling vs Streaming for status: Polling simpler; SSE reserved for scaling/perf improvements (future feature gating) to avoid premature infrastructure complexity.

## Performance Strategy
- Avoid re-creating chart objects; update series data incrementally.
- Use requestAnimationFrame for batch overlay redraws (Monte Carlo) throttled to last known stable data set.
- Pre-truncate or window large equity series (e.g., >25k points) via Brain-side downsampling (future FR) – not required for initial expected sizes.
- Memory watch: Provide dev utility to log series count and approximate memory (debug only, tree-shaken in prod).

## Accessibility & UX
- Ensure keyboard navigability of forms (native inputs + logical order).
- Tooltip focus: Provide accessible textual equivalents (e.g., selected bar OHLC displayed in aria-live region when user toggles keyboard nav mode).
- Color contrast tokens defined once; no pure-color reliance for critical states (use shape/outline for markers).

## Contracts Draft Summary
- CandlesPayload: { symbol, interval, from, to, candles: [ { t,o,h,l,c,v } ] }
- BacktestRunRequest: See data-model draft (StrategyConfig + RiskConfig embedded)
- BacktestRunStatus: { run_id, status, submitted_at, started_at?, completed_at?, error? }
- BacktestResultPayload: { run_id, metrics:{...}, equity:[{t,equity}], trades_summary:{count,win_rate,...}, validation:{ bootstrap:{...}, permutation:{...}, walkforward:{ splits:[...] } } }
- MonteCarloPathsPayload: { run_id, seed, p5:[{t,equity}], p95:[{t,equity}], paths:[ { path_id, points:[...] } ] }

## Open (Deferred) Items (Not Blocking)
- Background continuity if user closes tab mid-run (persist run id for recovery) – future enhancement.
- WebSocket / SSE upgrade for real-time streaming status.
- Advanced indicator scripting sandbox.
- Layout persistence & user customization.

## Risks & Mitigations
| Risk | Impact | Mitigation |
|------|--------|-----------|
| Performance degradation with many Monte Carlo paths | Slow UI & high memory | Custom canvas overlay + cap 500 paths + percentile shading default |
| Polling inefficiency at scale | Excess backend load | Backoff after 30s + aggregate status endpoint later |
| Indicator parameter explosion | Form clutter | Collapsible parameter groups + use defaults prominently |
| Large payload parse time | UI jank | Consider streaming/Chunk parse (deferred) + measure first |

## Conclusion
No blockers identified. LWC meets functional scope. Design path aligns with Constitution principles (determinism, simplicity). Ready for Phase 1 design artifacts.

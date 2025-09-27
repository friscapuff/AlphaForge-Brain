# Phase 1 Data Model (AlphaForge Mind Initial Tabs)

## Overview
Mind maintains lightweight TypeScript models mirroring Brain-produced artifacts. No mutation of computational results; transformations are pure projections for visualization.

## Entity Catalog
| Entity | Source | Purpose |
|--------|--------|---------|
| Candle | Brain (chart endpoint) | Candlestick & volume rendering |
| IndicatorConfig | Mind (user state) | Overlay configuration (enable/disable + params) |
| StrategyConfig | Mind (user input) | Parameterized strategy selection |
| RiskConfig | Mind (user input) | Risk controls transmitted to Brain |
| BacktestRunRequest | Mind → Brain | Initiate backtest run |
| BacktestRunStatus | Brain | Track run lifecycle |
| BacktestResult | Brain | Aggregate metrics + equity + validation outputs |
| MonteCarloPayload | Brain | Simulation paths + percentile bands |
| WalkForwardSplit | Brain | Train/test segments summary |
| PercentileBands (future) | Brain | Extended percentile arrays (p1, p5, p50, p95, p99) |

## TypeScript Interfaces (Draft)
```ts
export interface Candle { t: number; o: number; h: number; l: number; c: number; v: number }

export type IndicatorType = 'sma' | 'ema' | 'vwap' | 'bollinger' | 'volume';
export interface IndicatorConfig { id: string; type: IndicatorType; params: Record<string, number>; enabled: boolean }

export type StrategyParamType = 'number' | 'int' | 'enum' | 'bool';
export interface StrategyParam { name: string; value: number | string | boolean; type: StrategyParamType; min?: number; max?: number; options?: string[] }

export interface StrategyConfig { strategy_id: string; params: StrategyParam[]; version: string }

export type StopType = 'percent' | 'atr' | 'none';
export interface RiskConfig { position_size_pct: number; stop_type: StopType; stop_value?: number; take_profit?: number; daily_loss_cap?: number }

export interface ValidationToggle { bootstrap: boolean; permutation: boolean; walkforward: boolean; montecarlo: boolean; sensitivity?: boolean; regime?: boolean }

export interface BacktestRunRequest {
  date_from: string; // ISO
  date_to: string;   // ISO
  ticker: string;
  strategy: StrategyConfig;
  risk: RiskConfig;
  validation: ValidationToggle;
}

export type RunLifecycleStatus = 'queued' | 'running' | 'completed' | 'failed';
export interface BacktestRunStatus { run_id: string; status: RunLifecycleStatus; submitted_at: string; started_at?: string; completed_at?: string; error?: string }

export interface EquityPoint { t: number; equity: number }

export interface WalkForwardSplit { index: number; train_from: string; train_to: string; test_from: string; test_to: string; metrics: Record<string, number> }

export interface TradesSummary { count: number; win_rate: number; avg_win: number; avg_loss: number; profit_factor: number; expectancy: number }

export interface BacktestMetrics { cagr?: number; sharpe?: number; sortino?: number; max_drawdown?: number; volatility?: number; }

export interface BootstrapValidation { enabled: boolean; ci_lower?: number; ci_upper?: number; samples?: number }
export interface PermutationValidation { enabled: boolean; p_value?: number; permutations?: number }
export interface WalkForwardValidation { enabled: boolean; splits: WalkForwardSplit[] }

export interface ValidationSummary {
  bootstrap: BootstrapValidation;
  permutation: PermutationValidation;
  walkforward: WalkForwardValidation;
  // Optional future analyses
  sensitivity?: { enabled: boolean; param_impacts?: Record<string, number> };
  regime?: { enabled: boolean; regimes?: Array<{ label: string; metrics: Record<string, number> }> };
}

export interface BacktestResultPayload {
  run_id: string;
  metrics: BacktestMetrics;
  equity: EquityPoint[];
  trades_summary: TradesSummary;
  validation: ValidationSummary;
}

export interface MonteCarloPath { path_id: number; points: EquityPoint[] }

export interface ExtendedPercentiles { p1?: EquityPoint[]; p5?: EquityPoint[]; p50?: EquityPoint[]; p95?: EquityPoint[]; p99?: EquityPoint[] }

export interface MonteCarloPayload {
  run_id: string;
  seed: string;
  paths: MonteCarloPath[];
  // Required baseline bands
  p5: EquityPoint[];
  p95: EquityPoint[];
  // Optional extended percentiles (future expansion)
  extended?: ExtendedPercentiles;
}
```

## Percentile Expansion Design
Baseline render uses p5 & p95 (FR-017). Architecture allows future addition of p1, p50 (median), p99 without breaking existing consumers by placing them under `extended`. Rendering layer will detect presence and optionally allow user to cycle band presets: Narrow (p25–p75 future), Standard (p5–p95), Extreme (p1–p99).

## Validation Toggle Extensions
`sensitivity` (parameter sensitivity / importance) and `regime` (market regime segmentation) are optional flags. Initially disabled and omitted from BacktestRunRequest unless explicitly set. Brain ignoring unknown flags remains backward compatible (ADD-only contract evolution).

## Relationships
- BacktestRunRequest → (run_id) → BacktestRunStatus* (1..1 evolving)
- BacktestRunStatus(run_id completed) → BacktestResultPayload (1..1)
- BacktestResultPayload(run_id) ↔ MonteCarloPayload(run_id) (1..0..1 initial; may request separately)
- WalkForwardValidation.splits[] relates logically to equity timeline indices for annotation overlay.
- ExtendedPercentiles joined on time index alignment with equity.

## Normalization Strategy
- Flat arrays for time-series; no nested large structures to simplify diffing & memoization.
- MonteCarlo paths kept as array-of-paths; if performance issue emerges, flatten to struct-of-arrays (SoA) for faster overlay iteration (future optimization note).

## Validation Rules (Client-Side)
| Field | Rule |
|-------|------|
| date_from/date_to | date_from < date_to; warn if span >5y (FR-021) |
| ticker | Non-empty, single-token (no commas) |
| position_size_pct | 0 < value <= 100 |
| stop_value (percent) | 0 < value <= 50 (guard unrealistic) |
| strategy.params | Type-coerced & within min/max bounds |

## Determinism Notes
- No client randomization; Monte Carlo seed + path ordering preserved.
- Indicator calculations (if temporarily client-side) use pure deterministic loops with fixed precision (no locale/float rounding differences beyond IEEE defaults).
- Extended percentiles are purely additive; omission has no semantic effect on baseline metrics.

## Extensibility Considerations
- Additional indicators: extend IndicatorType union + params schema.
- Multi-ticker future: change ticker:string → tickers:string[]; isolate by centralized BacktestRunRequest builder.
- Additional percentile bands: populate `extended` object; consumers feature-detect keys.
- Sensitivity/regime detail expansions: embed structured arrays (versioned) inside existing optional objects; keep unknown-key ignore rule.

## Revisions
Version 0.2 Draft (2025-09-26) — added extended percentiles & validation toggle extensions.

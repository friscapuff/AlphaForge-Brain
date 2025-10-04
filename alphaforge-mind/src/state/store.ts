/**
 * Zustand Store (T029)
 * Provides chartSlice and backtestSlice minimal state scaffolding for integration tests.
 */
import { create } from 'zustand';

// ---- Types ----
export interface Candle {
  t: string; // ISO timestamp
  o: number; h: number; l: number; c: number; v: number;
}

export interface ChartState {
  symbol: string;
  range: string; // e.g. '1M'
  candles: Candle[];
  setSymbol: (s: string) => void;
  setRange: (r: string) => void;
  setCandles: (c: Candle[]) => void;
}

export interface BacktestRunSummary {
  runId: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  createdAt: string;
}

export interface BacktestResultMeta {
  equityCurve: Array<{ t: string; equity: number }>; // simplified
  metrics?: Record<string, number>;
  tradesSummary?: { count: number; win_rate: number };
  validation?: { bootstrap?: unknown; permutation?: unknown; walk_forward?: unknown };
  monteCarloPaths?: number[][]; // matrix of paths (time-aligned)
  walkForwardSplits?: Array<{ start: string; end: string; inSample: boolean }>; // for visualization
  /**
   * Validation caution badge (T043): when true, UI shows a caution indicator with metric tooltips.
   * Empty or falsey implies no caution.
   */
  validationCaution?: boolean;
  validationCautionMetrics?: string[];
  /**
   * Optimization deferral (T052): optimization_mode mirrors backend FR-013.
   * When 'deferred', UI shows a structured warning from advanced.warnings.
   */
  optimizationMode?: 'none' | 'deferred' | 'success' | string;
  advanced?: { warnings?: Array<{ code: string; [k: string]: unknown }> };
}

export interface BacktestState {
  runs: BacktestRunSummary[];
  selectedRunId?: string;
  results: Record<string, BacktestResultMeta | undefined>;
  lastRequest?: { start: string; end: string; strategy: string; equity: number; flags: { extendedPercentiles: boolean; advancedValidation: boolean } };
  selectRun: (id: string) => void;
  addRun: (run: BacktestRunSummary) => void;
  setResult: (id: string, meta: BacktestResultMeta) => void;
  setLastRequest: (req: { start: string; end: string; strategy: string; equity: number; flags: { extendedPercentiles: boolean; advancedValidation: boolean } }) => void;
}

export interface RootState extends ChartState, BacktestState {}

// ---- Slices ----
const chartSlice = (): ChartState => ({
  symbol: 'BTCUSD',
  range: '1M',
  candles: [],
  setSymbol(s) { this.symbol = s; },
  setRange(r) { this.range = r; },
  setCandles(c) { this.candles = c; },
});

const backtestSlice = (set: any, get: any): BacktestState => ({
  runs: [],
  results: {},
  lastRequest: undefined,
  selectRun: (id) => set((state: BacktestState) => ({ selectedRunId: id })),
  addRun: (run) => set((state: BacktestState) => ({ runs: [...state.runs, run] })),
  setResult: (id, meta) => set((state: BacktestState) => ({ results: { ...state.results, [id]: meta } })),
  setLastRequest: (req) => set((state: BacktestState) => ({ lastRequest: req })),
});

// ---- Store ----
export const useAppStore = create<RootState>()((set, get) => ({
  ...chartSlice(),
  ...backtestSlice(set, get),
}));

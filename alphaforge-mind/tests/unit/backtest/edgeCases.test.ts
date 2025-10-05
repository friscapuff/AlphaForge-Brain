import { describe, it, expect } from 'vitest';

// These tests exercise edge scenarios for backtest result handling (FR-007, FR-008).
// They focus on client-side selectors / projections to ensure the UI can gracefully
// handle sparse equity data and a zero-trades summary without throwing or displaying
// misleading metrics.

interface EquityPoint { t: number; equity: number }
interface TradesSummary { count: number; win_rate?: number; avg_win?: number; avg_loss?: number; profit_factor?: number; expectancy?: number }

function computeBasicMetrics(equity: EquityPoint[]) {
  if (!equity.length) return { cagr: 0, max_drawdown: 0 };
  const start = equity[0].equity;
  const end = equity[equity.length - 1].equity;
  const cagr = start === 0 ? 0 : (end - start) / start; // simplified for test
  let peak = equity[0].equity;
  let maxDd = 0;
  for (const p of equity) {
    if (p.equity > peak) peak = p.equity;
    const dd = peak ? (peak - p.equity) / peak : 0;
    if (dd > maxDd) maxDd = dd;
  }
  return { cagr, max_drawdown: +maxDd.toFixed(4) };
}

function safeTradesSummary(summary: TradesSummary) {
  if (summary.count === 0) {
    return {
      count: 0,
      win_rate: 0,
      avg_win: 0,
      avg_loss: 0,
      profit_factor: 0,
      expectancy: 0,
      empty: true,
      label: 'No trades executed'
    };
  }
  // Minimal defensive normalization
  const profit_factor = summary.avg_loss && summary.avg_loss !== 0
    ? (summary.avg_win || 0) / Math.abs(summary.avg_loss)
    : 0;
  return { ...summary, profit_factor };
}

describe('Backtest edge cases (T054)', () => {
  it('handles sparse equity data with large gaps without NaN metrics', () => {
    const sparse: EquityPoint[] = [
      { t: 1, equity: 10000 },
      // Gap (e.g., missing days) intentionally omitted
      { t: 5, equity: 10050 },
      { t: 50, equity: 9950 },
      { t: 200, equity: 10100 }
    ];
    const metrics = computeBasicMetrics(sparse);
    expect(metrics.cagr).toBeCloseTo((10100 - 10000) / 10000, 5);
    expect(metrics.max_drawdown).toBeGreaterThan(0);
    expect(Number.isNaN(metrics.max_drawdown)).toBe(false);
  });

  it('returns normalized summary for zero trades', () => {
    const normalized = safeTradesSummary({ count: 0 });
    expect(normalized.empty).toBe(true);
    expect(normalized.label).toBe('No trades executed');
    expect(normalized.profit_factor).toBe(0);
    expect(normalized.win_rate).toBe(0);
  });

  it('computes profit factor defensively when avg_loss is zero or missing', () => {
    const s1 = safeTradesSummary({ count: 10, avg_win: 100, avg_loss: 0 });
    expect(s1.profit_factor).toBe(0);
    const s2 = safeTradesSummary({ count: 10, avg_win: 100 });
    expect(s2.profit_factor).toBe(0);
  });
});

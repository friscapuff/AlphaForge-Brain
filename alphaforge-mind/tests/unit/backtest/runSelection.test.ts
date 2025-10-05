// T014 Run id mapping & selection logic
import { describe, it, expect } from 'vitest';

interface RunMeta { run_id: string; created_at: number; symbol: string; }

function selectMostRecent(runs: RunMeta[], symbol: string): string | null {
  return runs
    .filter(r => r.symbol === symbol)
    .sort((a,b) => b.created_at - a.created_at)[0]?.run_id ?? null;
}

describe('T014 run selection', () => {
  const base = Date.now();
  const runs = [
    { run_id: 'r1', created_at: base - 1000, symbol: 'AAPL' },
    { run_id: 'r2', created_at: base - 500, symbol: 'AAPL' },
    { run_id: 'r3', created_at: base - 50, symbol: 'MSFT' },
  ];
  it('picks most recent for symbol', () => {
    expect(selectMostRecent(runs, 'AAPL')).toBe('r2');
  });
  it('returns null when none', () => {
    expect(selectMostRecent(runs, 'NVDA')).toBeNull();
  });
});

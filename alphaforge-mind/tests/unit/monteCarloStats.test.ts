import { describe, it, expect } from 'vitest';
import { computeMonteCarloStats } from '../../src/utils/monteCarloStats.js';

function genPaths(nPaths: number, nPoints: number): number[][] {
  const out: number[][] = [];
  for (let p=0;p<nPaths;p++) {
    const arr: number[] = [];
    let v = 100 + p; // slight offset per path
    for (let i=0;i<nPoints;i++) { v += Math.sin(i/5) * 0.1; arr.push(Number(v.toFixed(4))); }
    out.push(arr);
  }
  return out;
}

describe('computeMonteCarloStats', () => {
  it('returns null for fewer than 3 paths (optimization)', () => {
    expect(computeMonteCarloStats(genPaths(0, 10))).toBeNull();
    expect(computeMonteCarloStats(genPaths(1, 10))).toBeNull();
    expect(computeMonteCarloStats(genPaths(2, 10))).toBeNull();
  });

  it('computes percentile arrays with expected lengths and ordering', () => {
    const paths = genPaths(20, 30);
    const stats = computeMonteCarloStats(paths);
    expect(stats).not.toBeNull();
    if (!stats) return;
    expect(stats.nPoints).toBe(30);
    expect(stats.p05.length).toBe(30);
    expect(stats.p50.length).toBe(30);
    expect(stats.p95.length).toBe(30);
    // For each point p05 <= p50 <= p95
    for (let i=0;i<stats.nPoints;i++) {
      expect(stats.p05[i]).toBeLessThanOrEqual(stats.p50[i]);
      expect(stats.p50[i]).toBeLessThanOrEqual(stats.p95[i]);
    }
  });

  it('handles identical value paths by padding range', () => {
    const paths = Array.from({length: 5}, () => Array.from({length: 10}, () => 42));
    const stats = computeMonteCarloStats(paths);
    expect(stats).not.toBeNull();
    if (!stats) return;
    expect(stats.gmin).toBeLessThan(stats.gmax); // expanded artificially
  });
});

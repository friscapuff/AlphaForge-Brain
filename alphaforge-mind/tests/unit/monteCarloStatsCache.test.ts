import { describe, it, expect } from 'vitest';
import { computeMonteCarloStatsCached } from '../../src/utils/monteCarloStats.js';

function makePaths(nP: number, nPts: number) {
  const arr: number[][] = [];
  for (let p=0;p<nP;p++) {
    const row: number[] = []; let v = 100 + p;
    for (let i=0;i<nPts;i++) { v += 0.01; row.push(v); }
    arr.push(row);
  }
  return arr;
}

describe('computeMonteCarloStatsCached', () => {
  it('caches result for same reference', () => {
    const paths = makePaths(10, 20);
    const a = computeMonteCarloStatsCached(paths);
    const b = computeMonteCarloStatsCached(paths);
    expect(a).toBe(b); // same object instance
  });
  it('recomputes for new array reference', () => {
    const paths = makePaths(10, 20);
    const a = computeMonteCarloStatsCached(paths);
    const newPaths = [...paths]; // shallow copy new reference
    const b = computeMonteCarloStatsCached(newPaths);
    expect(a).not.toBe(b);
  });
});

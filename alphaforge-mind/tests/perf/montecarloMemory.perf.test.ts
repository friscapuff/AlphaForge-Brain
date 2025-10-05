import { describe, it, expect } from 'vitest';
import { estimateMatrixBytes, generateMonteCarloMatrix, formatMB } from './mcPerfUtils.js';

/**
 * T090 Memory usage capture (200 paths + equity) <75MB
 * We approximate memory by counting matrix bytes + equity curve (points * 8).
 * This is a static analytical test (not runtime RSS) to keep it deterministic in CI.
 */

describe('T090 Monte Carlo memory analytical bound', () => {
  it('estimated footprint for 200 paths x 500 points + equity < 75MB', () => {
    const PATHS = 200;
    const POINTS = 500; // representative horizon length
    const matrixBytes = estimateMatrixBytes(PATHS, POINTS);
    const equityBytes = estimateMatrixBytes(1, POINTS); // single equity curve
    const total = matrixBytes + equityBytes;
    const totalMB = total / (1024 * 1024);
    // Soft assertion: < 75MB (target from tasks spec)
    expect(totalMB).toBeLessThan(75);
    if (totalMB > 60) {
      // eslint-disable-next-line no-console
      console.warn(`[T090] Memory near threshold: ${formatMB(total)} (matrix=${formatMB(matrixBytes)})`);
    }
  });
});

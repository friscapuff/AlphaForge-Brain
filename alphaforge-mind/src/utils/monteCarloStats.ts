export interface MonteCarloStats { gmin: number; gmax: number; p05: number[]; p50: number[]; p95: number[]; nPoints: number; }

/**
 * Compute percentile bands (5/50/95) for aligned Monte Carlo paths.
 * Returns null if invalid input or fewer than 3 paths (micro-optimization early exit).
 */
export function computeMonteCarloStats(paths: number[][] | undefined | null): MonteCarloStats | null {
  if (!paths || paths.length < 3) return null; // skip when insufficient diversity
  const nPoints = paths[0]?.length ?? 0;
  if (nPoints === 0) return null;
  let gmin = Infinity, gmax = -Infinity;
  for (const p of paths) {
    if (!p || p.length !== nPoints) return null; // inconsistent lengths
    for (const v of p) { if (v < gmin) gmin = v; if (v > gmax) gmax = v; }
  }
  if (!isFinite(gmin) || !isFinite(gmax) || gmin === gmax) { gmin = gmin - 1; gmax = gmax + 1; }
  const p05: number[] = new Array(nPoints);
  const p50: number[] = new Array(nPoints);
  const p95: number[] = new Array(nPoints);
  const scratch = new Array(paths.length);
  for (let i = 0; i < nPoints; i++) {
    for (let r = 0; r < paths.length; r++) scratch[r] = paths[r][i];
    scratch.sort((a,b)=>a-b);
    const pick = (q: number) => scratch[Math.min(scratch.length-1, Math.floor(q * scratch.length))];
    p05[i] = pick(0.05); p50[i] = pick(0.5); p95[i] = pick(0.95);
  }
  return { gmin, gmax, p05, p50, p95, nPoints };
}

// WeakMap cache keyed by the outer array reference. If caller mutates in place this won't invalidate;
// assumption: new computation triggers new array reference (typical immutable state patterns).
const _cache = new WeakMap<number[][], MonteCarloStats | null>();

export function computeMonteCarloStatsCached(paths: number[][] | undefined | null): MonteCarloStats | null {
  if (!paths) return null;
  if (_cache.has(paths)) return _cache.get(paths) ?? null;
  const stats = computeMonteCarloStats(paths);
  _cache.set(paths, stats);
  return stats;
}

/**
 * seriesTransforms (T058)
 * Shared lightweight helpers for normalizing numeric time-series data used by
 * EquityCurveChart and MonteCarloOverlay to avoid duplicated min/max scans and
 * path construction logic scattered across components.
 */

export interface NumericPoint { v: number }

export interface NormalizedSeriesResult<T = NumericPoint> {
  min: number; max: number; span: number; points: T[]; normalize: (value: number) => number;
}

export function normalizeSeries<T extends Record<string, any>>(points: T[], accessor: (p: T) => number): NormalizedSeriesResult<T> {
  if (!points.length) return { min: 0, max: 0, span: 0, points: [], normalize: () => 0 };
  let min = Infinity, max = -Infinity;
  for (const p of points) {
    const v = accessor(p);
    if (v < min) min = v;
    if (v > max) max = v;
  }
  if (!isFinite(min) || !isFinite(max)) return { min: 0, max: 0, span: 0, points: [], normalize: () => 0 };
  const span = max - min || 1;
  const normalize = (value: number) => (value - min) / span;
  return { min, max, span, points, normalize };
}

export function buildSimplePath<T>(norm: NormalizedSeriesResult<T>, accessor: (p: T) => number, height = 50, xStep = 4): string {
  if (!norm.points.length) return '';
  let path = '';
  for (let i = 0; i < norm.points.length; i++) {
    const p = norm.points[i] as any;
    const n = norm.normalize(accessor(p));
    const x = i * xStep;
    const y = height - n * height;
    path += `${i === 0 ? 'M' : 'L'} ${x} ${y} `;
  }
  return path.trim();
}

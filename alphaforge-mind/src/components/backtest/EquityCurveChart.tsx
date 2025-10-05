import React, { useMemo } from 'react';
import { normalizeSeries, buildSimplePath } from '../../utils/seriesTransforms.js';
import { useAppStore } from '../../state/store.js';

/**
 * EquityCurveChart (T038)
 * Placeholder SVG line chart stub; will integrate real charting later.
 */
export function EquityCurveChart(): React.ReactElement {
  const selected = useAppStore(s => s.selectedRunId);
  const result = useAppStore(s => (selected ? s.results[selected] : undefined));
  const points = result?.equityCurve || [];
  const derived = useMemo(() => {
    if (!points.length) return null;
    const norm = normalizeSeries(points, p => p.equity);
    const path = buildSimplePath(norm, p => p.equity, 50, 4);
    return { path, width: points.length * 4 };
  }, [points]);
  if (!derived) return React.createElement('div', { className: 'text-xs text-neutral-500' }, 'No equity data');
  return React.createElement('svg', { width: derived.width, height: 50, className: 'border border-neutral-700 bg-neutral-900' },
    React.createElement('path', { d: derived.path, fill: 'none', stroke: '#4ade80', strokeWidth: 1 })
  );
}

export default EquityCurveChart;

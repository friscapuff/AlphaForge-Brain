import React from 'react';
import { useAppStore } from '../../state/store.js';

/** MetricsGrid (T039) */
export function MetricsGrid(): React.ReactElement {
  const selected = useAppStore(s => s.selectedRunId);
  const metrics = useAppStore(s => (selected ? s.results[selected]?.metrics : undefined));
  if (!metrics) return React.createElement('div', { className: 'text-xs text-neutral-500' }, 'No metrics');
  return React.createElement(
    'div',
    { className: 'grid grid-cols-3 gap-2 text-xs' },
    Object.entries(metrics).map(([k, v]) =>
      React.createElement(
        'div',
        { key: k, className: 'p-2 rounded bg-neutral-800 border border-neutral-700' },
        `${k}: ${v}`
      )
    )
  );
}
export default MetricsGrid;

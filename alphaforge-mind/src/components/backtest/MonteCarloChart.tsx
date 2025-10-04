import React from 'react';
import { useAppStore } from '../../state/store.js';

/** MonteCarloChart (T043) - placeholder visualizing path endpoints */
export function MonteCarloChart(): React.ReactElement {
  const selected = useAppStore(s => s.selectedRunId);
  const paths = useAppStore(s => (selected ? s.results[selected]?.monteCarloPaths : undefined));
  if (!paths || paths.length === 0) return React.createElement('div', { className: 'text-xs text-neutral-500' }, 'No MC paths');
  const lastValues = paths.map(p => p[p.length - 1]);
  const min = Math.min(...lastValues);
  const max = Math.max(...lastValues);
  const norm = (v: number) => (max === min ? 0.5 : (v - min) / (max - min));
  return React.createElement(
    'div',
    { className: 'flex gap-0.5 items-end h-24' },
    lastValues.map((v, i) => React.createElement('div', {
      key: i,
      style: { height: `${20 + norm(v) * 60}%` },
      className: 'w-1 bg-purple-500'
    }))
  );
}
export default MonteCarloChart;

import React from 'react';
import { useAppStore } from '../../state/store.js';

/** WalkForwardSplitsChart (T042) */
export function WalkForwardSplitsChart(): React.ReactElement {
  const selected = useAppStore(s => s.selectedRunId);
  const splits = useAppStore(s => (selected ? s.results[selected]?.walkForwardSplits : undefined));
  if (!splits || splits.length === 0) return React.createElement('div', { className: 'text-xs text-neutral-500' }, 'No splits');
  return React.createElement(
    'div',
    { className: 'flex gap-1' },
    splits.map((sp, i) => React.createElement(
      'div',
      {
        key: i,
        title: `${sp.start} → ${sp.end}`,
        className: `${sp.inSample ? 'bg-green-600' : 'bg-blue-600'} h-3 flex-1 rounded-sm`
      }
    ))
  );
}
export default WalkForwardSplitsChart;

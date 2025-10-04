import React from 'react';
import { useAppStore } from '../../state/store.js';

/**
 * RunHistory (T037)
 * Displays list of runs and allows selecting one.
 */
export function RunHistory(): React.ReactElement {
  const runs = useAppStore(s => s.runs);
  const selectRun = useAppStore(s => s.selectRun);
  const selected = useAppStore(s => s.selectedRunId);
  if (!runs.length) return React.createElement('div', { className: 'text-xs text-neutral-500' }, 'No runs yet');
  return React.createElement(
    'ul',
    { className: 'space-y-1 text-xs' },
    runs.map(r => React.createElement(
      'li',
      { key: r.runId },
      React.createElement(
        'button',
        {
          type: 'button',
          onClick: () => selectRun(r.runId),
          className: `${selected === r.runId ? 'font-bold text-green-400' : 'text-neutral-300'} underline`
        },
        `${r.runId} (${r.status})`
      )
    ))
  );
}

export default RunHistory;

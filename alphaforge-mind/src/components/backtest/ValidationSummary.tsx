import React from 'react';
import { useAppStore } from '../../state/store.js';

/** ValidationSummary (T041) */
export function ValidationSummary(): React.ReactElement {
  const selected = useAppStore(s => s.selectedRunId);
  const validation = useAppStore(s => (selected ? s.results[selected]?.validation : undefined));
  if (!validation) return React.createElement('div', { className: 'text-xs text-neutral-500' }, 'No validation data');
  return React.createElement(
    'pre',
    { className: 'text-[10px] bg-neutral-900 border border-neutral-700 p-2 rounded overflow-x-auto max-h-40' },
    JSON.stringify(validation, null, 2)
  );
}
export default ValidationSummary;

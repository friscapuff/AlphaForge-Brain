import React from 'react';
import { useAppStore } from '../../state/store.js';

/** TradesSummaryTable (T040) */
export function TradesSummaryTable(): React.ReactElement {
  const selected = useAppStore(s => s.selectedRunId);
  const tradesSummary = useAppStore(s => (selected ? s.results[selected]?.tradesSummary : undefined));
  if (!tradesSummary) return React.createElement('div', { className: 'text-xs text-neutral-500' }, 'No trades summary');
  return React.createElement(
    'table',
    { className: 'text-xs border border-neutral-700 w-auto' },
    React.createElement(
      'thead',
      null,
      React.createElement(
        'tr',
        null,
        React.createElement('th', { className: 'px-2 py-1 border border-neutral-700' }, 'count'),
        React.createElement('th', { className: 'px-2 py-1 border border-neutral-700' }, 'win_rate')
      )
    ),
    React.createElement(
      'tbody',
      null,
      React.createElement(
        'tr',
        null,
        React.createElement('td', { className: 'px-2 py-1 border border-neutral-700' }, String(tradesSummary.count)),
        React.createElement('td', { className: 'px-2 py-1 border border-neutral-700' }, String(tradesSummary.win_rate))
      )
    )
  );
}
export default TradesSummaryTable;

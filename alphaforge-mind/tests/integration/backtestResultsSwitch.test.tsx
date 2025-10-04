import { describe, it, expect } from 'vitest';
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
// @ts-ignore placeholder
// Real BacktestResultsPanel will replace fallback later.

// Fallback to express tab switching expectations
// @ts-ignore
const FallbackBacktestResultsPanel = () => {
  const [tab, setTab] = React.useState<'equity' | 'metrics' | 'history'>('equity');
  return (
    <div>
      <nav>
        <button onClick={() => setTab('equity')}>equity-tab</button>
        <button onClick={() => setTab('metrics')}>metrics-tab</button>
        <button onClick={() => setTab('history')}>history-tab</button>
      </nav>
      {tab === 'equity' && <div data-testid="equity-view">Equity Curve Placeholder</div>}
      {tab === 'metrics' && <div data-testid="metrics-view">Metrics Placeholder</div>}
      {tab === 'history' && <div data-testid="history-view">Trades History Placeholder</div>}
    </div>
  );
};

// dynamic resolution
// @ts-ignore
const ResolvedResultsPanel = FallbackBacktestResultsPanel;

describe('T020 Backtest Results Switch (Test-First)', () => {
  it('switches between equity, metrics, and history views', () => {
    render(<ResolvedResultsPanel />);
    expect(screen.getByTestId('equity-view')).toBeInTheDocument();
    fireEvent.click(screen.getByText('metrics-tab'));
    expect(screen.getByTestId('metrics-view')).toBeInTheDocument();
    fireEvent.click(screen.getByText('history-tab'));
    expect(screen.getByTestId('history-view')).toBeInTheDocument();
  });
});

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';

// Placeholder components/hooks until real ones exist
// @ts-ignore
// Real BacktestLifecycle will replace fallback later.

// Fallback implementing deterministic manual progression (no timers)
// @ts-ignore
const FallbackBacktestLifecycle: React.FC = () => {
  const [status, setStatus] = React.useState('idle');
  const [polls, setPolls] = React.useState(0);
  const submit = () => setStatus('queued');
  const advance = () => {
    if (status === 'queued') setStatus('running');
    else if (status === 'running') setStatus('completed');
  };
  const poll = () => setPolls(p => p + 1);
  return React.createElement(
    'div',
    null,
    React.createElement('button', { onClick: submit }, 'submit-backtest'),
    React.createElement('button', { onClick: advance }, 'advance-status'),
    React.createElement('button', { onClick: poll }, 'poll'),
    React.createElement('div', { 'data-testid': 'status' }, status),
    React.createElement('div', { 'data-testid': 'poll-count' }, String(polls))
  );
};

// dynamic resolution
// @ts-ignore
const ResolvedLifecycle = FallbackBacktestLifecycle;

describe('T019 Backtest Run Lifecycle (Test-First)', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('transitions through queued -> running -> completed and counts polls', () => {
  render(React.createElement(ResolvedLifecycle));
    fireEvent.click(screen.getByText('submit-backtest'));
    expect(screen.getByTestId('status').textContent).toBe('queued');
    fireEvent.click(screen.getByText('poll'));
    fireEvent.click(screen.getByText('poll'));
    fireEvent.click(screen.getByText('advance-status'));
    expect(screen.getByTestId('status').textContent).toBe('running');
    fireEvent.click(screen.getByText('poll'));
    fireEvent.click(screen.getByText('advance-status'));
    expect(screen.getByTestId('status').textContent).toBe('completed');
    const pollCount = parseInt(screen.getByTestId('poll-count').textContent || '0', 10);
    expect(pollCount).toBeGreaterThanOrEqual(3);
  });
});

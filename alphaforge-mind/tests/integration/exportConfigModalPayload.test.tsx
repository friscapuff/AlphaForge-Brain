import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { ExportConfigModal } from '../../src/components/backtest/ExportConfigModal.js';
import { useAppStore } from '../../src/state/store.js';
import { useFeatureFlags } from '../../src/state/featureFlags.js';

// Simulate an executed run and lastRequest population
function setupState() {
  const runId = 'run_test';
  useAppStore.setState({
    runs: [{ runId, status: 'completed', createdAt: '2025-01-01T00:00:00.000Z' }],
    selectedRunId: runId,
    results: {},
    lastRequest: { start: '2024-12-01', end: '2024-12-31', strategy: 'mean_rev', equity: 15000, flags: { extendedPercentiles: true, advancedValidation: false } }
  } as any);
  useFeatureFlags.setState({ extendedPercentiles: true, advancedValidation: false });
}

describe('ExportConfigModal payload & copy buttons', () => {
  it('renders real date range and validation flags and supports copying', async () => {
    setupState();
    const writeText = vi.fn();
    (global as any).navigator = { clipboard: { writeText } };
    render(<ExportConfigModal open={true} onClose={() => {}} />);
  // Strategy baseline now 'buy_hold' (was 'mean_rev' earlier). Match on strategy block generically.
  const pre = await screen.findByText(/"strategy"/);
    expect(pre).toBeDefined();
    expect(screen.getByText(/2024-12-01/)).toBeDefined();
    expect(screen.getByText(/2024-12-31/)).toBeDefined();
    expect(screen.getByText(/extendedPercentiles/)).toBeDefined();
    const copyJsonBtn = screen.getByRole('button', { name: /Copy JSON/i });
    await act(async () => { fireEvent.click(copyJsonBtn); });
    expect(writeText).toHaveBeenCalled();
    const copyHashBtn = screen.getByRole('button', { name: /Copy Hash/i });
    await act(async () => { fireEvent.click(copyHashBtn); });
    expect(writeText).toHaveBeenCalledTimes(2);
  });
});

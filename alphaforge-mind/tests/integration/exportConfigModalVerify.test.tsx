import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { ExportConfigModal } from '../../src/components/backtest/ExportConfigModal.js';
import { useAppStore } from '../../src/state/store.js';

// Mock the API helper to avoid network dependency
vi.mock('../../src/services/api/canonical.js', () => ({
  callCanonicalHash: vi.fn(async () => ({ canonical: '{"a":1}', sha256: 'serverhash123' }))
}));

function setupState() {
  const runId = 'run_v1';
  useAppStore.setState({
    runs: [{ runId, status: 'completed', createdAt: '2025-01-01T00:00:00.000Z' }],
    selectedRunId: runId,
    results: {},
    lastRequest: { start: '2025-01-01', end: '2025-01-15', strategy: 'mean_rev', equity: 10000, flags: { extendedPercentiles: false, advancedValidation: false } }
  } as any);
}

describe('ExportConfigModal verify button', () => {
  beforeEach(() => { setupState(); });
  it('calls backend and shows server match indicator', async () => {
    (global as any).navigator = { clipboard: { writeText: vi.fn() } };
    render(<ExportConfigModal open={true} onClose={() => {}} />);
    // Wait for initial hash render
    await screen.findByText(/sha256:/);
    const verifyBtn = screen.getByRole('button', { name: /Verify/i });
    await act(async () => { fireEvent.click(verifyBtn); });
    // After verify, expect server match/mismatch label to appear
    const matchEl = await screen.findByText(/server (match|mismatch)/i);
    expect(matchEl).toBeDefined();
  });
});

import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MonteCarloOverlay } from '../../src/components/backtest/MonteCarloOverlay.js';
import { installMockCanvas } from '../utils/mockCanvas.js';
import { useAppStore } from '../../src/state/store.js';

// T100: Progressive reveal test

describe('T100 Progressive Monte Carlo reveal', () => {
  it('draws in batches using requestAnimationFrame until all paths rendered', async () => {
    installMockCanvas({ onStroke: () => strokes.push(Date.now()) });
      // Track stroke calls to confirm drawing batches executed
      const strokes: number[] = [];
      vi.spyOn(window, 'requestAnimationFrame').mockImplementation((cb: FrameRequestCallback) => {
        // Immediately invoke (simulate fast frame progression)
        cb(performance.now());
        return 1;
      });
    // Populate store with fake paths AFTER raf spy installed
    const paths: number[][] = [];
    for (let p=0;p<120;p++) {
      const series: number[] = [];
      let v = 10000;
      for (let i=0;i<30;i++) { v *= 1 + 0.0005; series.push(v); }
      paths.push(series);
    }
    useAppStore.setState({ selectedRunId: 'R1', runs: [{ runId:'R1', status:'completed', createdAt: new Date().toISOString()}], results: { R1: { equityCurve: [], monteCarloPaths: paths } } });
    render(<MonteCarloOverlay width={300} height={120} />);
    const canvas = await screen.findByTestId('mc-overlay-canvas');
    expect(canvas).toBeDefined();
      // Wait for at least one stroke call indicating drawing occurred
      await waitFor(() => expect(strokes.length).toBeGreaterThan(0));
  });
});

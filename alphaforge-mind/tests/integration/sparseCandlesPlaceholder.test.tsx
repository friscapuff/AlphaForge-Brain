import { describe, it, expect } from 'vitest';
import React from 'react';
import { render, screen } from '@testing-library/react';
import { CandleChart } from '../../src/components/charts/CandleChart.js';

// T099: Sparse OHLCV placeholder behavior

describe('T099 Sparse OHLCV placeholders', () => {
  it('renders gap indicator element when large timestamp gap detected', () => {
    const now = Date.now();
    const day = 24*3600*1000;
    const data = [
      { time: now - 10*day, open: 1, high: 2, low: 0.5, close: 1.5 },
      { time: now, open: 2, high: 3, low: 1.8, close: 2.5 }
    ];
    render(<CandleChart data={data} height={120} />);
    expect(screen.getByTestId('candle-gap-indicator')).toBeDefined();
  });
});

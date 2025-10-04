import { useState, useMemo } from 'react';
import { IndicatorPanel } from '../components/charts/IndicatorPanel.js';

export function ChartAnalysisPage() {
  const [symbol, setSymbol] = useState('AAPL');
  // Temporary mock candle data until API wiring (useCandles + store) is integrated into the page
  const mockCandles = useMemo(
    () =>
      Array.from({ length: 50 }).map((_, i) => {
        const base = 100 + i * 0.2;
        const open = base + Math.sin(i / 3) * 2;
        const close = open + (Math.random() - 0.5) * 2;
        const high = Math.max(open, close) + Math.random() * 1.5;
        const low = Math.min(open, close) - Math.random() * 1.5;
        return {
          time: Date.now() / 1000 - (50 - i) * 3600,
          open: Number(open.toFixed(2)),
          high: Number(high.toFixed(2)),
          low: Number(low.toFixed(2)),
          close: Number(close.toFixed(2)),
          volume: Math.round(1000 + Math.random() * 500),
        };
      }),
    []
  );

  return (
    <div className="p-4 space-y-4">
      <h1 className="text-xl font-semibold">Chart Analysis</h1>
      <div className="flex items-center gap-2">
        <label className="text-sm">Symbol</label>
        <input
          value={symbol}
          onChange={e => setSymbol(e.target.value.toUpperCase())}
          className="px-2 py-1 rounded bg-neutral-800 border border-neutral-700"
        />
      </div>
      <IndicatorPanel candles={mockCandles} />
    </div>
  );
}

import React, { useEffect, useRef } from 'react';

/**
 * CandleChart (T032)
 * Lightweight wrapper prepared for integrating `lightweight-charts` (or similar) in a later task.
 * For now this is a pure skeleton so downstream composition (IndicatorPanel) can be scaffolded.
 *
 * Assumptions:
 *  - We'll dynamically import the charting lib later to keep bundle lean.
 *  - Props kept minimal; will extend with series management & resize observer subsequently.
 */

export interface CandleDataPoint {
  time: number | string; // epoch seconds or business day string; concrete type refined later
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

export interface CandleChartProps {
  data: CandleDataPoint[];
  className?: string;
  height?: number;
  /** Placeholder for future onReady callback delivering imperative chart API */
  onReady?: (api: unknown) => void; // will refine type
}

export function CandleChart({ data, className, height = 360, onReady }: CandleChartProps): React.ReactElement {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartApiRef = useRef<unknown>(null); // will hold library instance later

  // Effect placeholder for future dynamic import + chart creation
  useEffect(() => {
    // Intentionally left as a no-op until chart lib integrated.
    if (onReady && chartApiRef.current) {
      onReady(chartApiRef.current);
    }
  }, [onReady]);

  // Effect placeholder for applying data updates (will diff or set series later)
  useEffect(() => {
    // no-op now
  }, [data]);

  // Sparse gap heuristic: if any adjacent candle gap > 5 days (in ms) mark placeholder
  let hasGap = false;
  if (data && data.length >= 2) {
    for (let i=1;i<data.length;i++) {
      const prev = data[i-1].time as number;
      const curr = data[i].time as number;
      if (typeof prev === 'number' && typeof curr === 'number' && (curr - prev) > 5*24*3600*1000) { hasGap = true; break; }
    }
  }
  return (
    <div
      ref={containerRef}
      className={className}
      style={{
        position: 'relative', width: '100%', height,
        background: '#0f1115', border: '1px solid #1e222d', borderRadius: 4,
        fontFamily: 'system-ui, sans-serif', display: 'flex', alignItems: 'center', justifyContent: 'center',
        color: '#556', userSelect: 'none'
      } as React.CSSProperties}
    >
      <span style={{ fontSize: 12, opacity: 0.6 } as React.CSSProperties}>Chart initializing… (stub)</span>
      {hasGap && <div data-testid="candle-gap-indicator" style={{ position:'absolute', top:4, right:4, fontSize:10, background:'#332244', padding:'2px 4px', borderRadius:3 }}>Gaps</div>}
    </div>
  );
}

export default CandleChart;

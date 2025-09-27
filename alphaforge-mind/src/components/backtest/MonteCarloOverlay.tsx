/**
 * MonteCarloOverlay (T044)
 * Batch draws Monte Carlo equity paths to a single canvas for performance.
 */
import React, { useEffect, useRef, useMemo } from 'react';
import { useAppStore } from '../../state/store.js';
import { computeMonteCarloStatsCached } from '../../utils/monteCarloStats.js';

export interface MonteCarloOverlayProps {
  width?: number;
  height?: number;
  stroke?: string;
  alpha?: number;
}

export const MonteCarloOverlay: React.FC<MonteCarloOverlayProps> = ({ width = 400, height = 200, stroke = '#6b5b95', alpha = 0.15 }) => {
  const selected = useAppStore(s => s.selectedRunId);
  const paths = useAppStore(s => (selected ? s.results[selected]?.monteCarloPaths : undefined));
  // Memoize flattened stats to avoid recomputation on unrelated re-renders (e.g., parent state changes)
  const stats = useMemo(() => computeMonteCarloStatsCached(paths), [paths]);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.clearRect(0, 0, width, height);
    if (!paths || paths.length === 0 || !stats) return;
    const { gmin, gmax, p05, p50, p95, nPoints } = stats;
    const xStep = width / Math.max(1, nPoints - 1);

    // Draw percentile band (p05-p95) first
    ctx.save();
    ctx.globalAlpha = 0.08;
    ctx.fillStyle = '#836fff';
    ctx.beginPath();
    for (let i=0;i<nPoints;i++) {
      const x = i * xStep;
      const norm = (p95[i] - gmin) / (gmax - gmin);
      const y = height - norm * height;
      if (i===0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    for (let i=nPoints-1;i>=0;i--) {
      const x = i * xStep;
      const norm = (p05[i] - gmin) / (gmax - gmin);
      const y = height - norm * height;
      ctx.lineTo(x, y);
    }
    ctx.closePath();
    ctx.fill();
    ctx.restore();

    // Median line
    ctx.save();
  ctx.globalAlpha = 0.6;
    ctx.strokeStyle = '#b19cd9';
    ctx.beginPath();
    for (let i=0;i<nPoints;i++) {
      const x = i * xStep;
      const norm = (p50[i] - gmin) / (gmax - gmin);
      const y = height - norm * height;
      if (i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
    }
    ctx.stroke();
    ctx.restore();

    // rAF chunked path drawing
    let index = 0;
    ctx.globalAlpha = alpha;
    ctx.lineWidth = 1;
    ctx.strokeStyle = stroke;
  const batch = 40; // tuned batch size after T055 refinement for fewer frames
    function drawBatch() {
      if (!paths || !ctx) return;
      const end = Math.min(paths.length, index + batch);
      for (; index < end; index++) {
        const p = paths[index];
        if (!p) continue;
        ctx.beginPath();
        for (let i=0;i<p.length;i++) {
          const x = i * xStep;
          const norm = (p[i] - gmin) / (gmax - gmin);
          const y = height - norm * height;
          if (i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
        }
        ctx.stroke();
      }
      if (index < paths.length) (window.requestAnimationFrame || ((cb: FrameRequestCallback) => setTimeout(() => cb(performance.now()), 16)))(drawBatch);
    }
    (window.requestAnimationFrame || ((cb: FrameRequestCallback) => setTimeout(() => cb(performance.now()), 16)))(drawBatch);
  }, [paths, width, height, stroke, alpha]);

  if (!paths || paths.length === 0) return <div className="text-xs text-neutral-500">No MC paths</div>;
  return <canvas data-testid="mc-overlay-canvas" ref={canvasRef} width={width} height={height} className="border border-neutral-700 rounded" />;
};

export default MonteCarloOverlay;

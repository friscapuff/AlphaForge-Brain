/**
 * MonteCarloOverlay (T044)
 * Batch draws Monte Carlo equity paths to a single canvas for performance.
 * - Accepts matrix of paths (each path = number[] of equity values)
 * - Scales values to canvas height; x = index spacing
 * - Future: color coding percentiles, progressive reveal, rAF batching
 */
import React, { useEffect, useRef } from 'react';
import { useAppStore } from '../../state/store.js';

export interface MonteCarloOverlayProps {
  width?: number;
  height?: number;
  stroke?: string;
  alpha?: number;
}

export const MonteCarloOverlay: React.FC<MonteCarloOverlayProps> = ({ width = 400, height = 200, stroke = '#6b5b95', alpha = 0.15 }) => {
  const selected = useAppStore(s => s.selectedRunId);
  const paths = useAppStore(s => (selected ? s.results[selected]?.monteCarloPaths : undefined));
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.clearRect(0, 0, width, height);
    if (!paths || paths.length === 0) return;

    // Gather global min/max
    let gmin = Infinity, gmax = -Infinity;
    for (const p of paths) {
      for (const v of p) {
        if (v < gmin) gmin = v;
        if (v > gmax) gmax = v;
      }
    }
    if (!isFinite(gmin) || !isFinite(gmax) || gmin === gmax) {
      gmin = gmin === gmax ? gmin - 1 : gmin;
      gmax = gmax === gmin ? gmax + 1 : gmax;
    }

    const nPoints = paths[0].length;
    const xStep = width / Math.max(1, nPoints - 1);
    ctx.globalAlpha = alpha;
    ctx.lineWidth = 1;
    ctx.strokeStyle = stroke;

    for (const p of paths) {
      ctx.beginPath();
      for (let i = 0; i < p.length; i++) {
        const x = i * xStep;
        const norm = (p[i] - gmin) / (gmax - gmin);
        const y = height - norm * height;
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      }
      ctx.stroke();
    }
  }, [paths, width, height, stroke, alpha]);

  if (!paths || paths.length === 0) {
    return React.createElement('div', { className: 'text-xs text-neutral-500' }, 'No MC paths');
  }
  return React.createElement('canvas', { 'data-testid': 'mc-overlay-canvas', ref: canvasRef, width, height, className: 'border border-neutral-700 rounded' });
};

export default MonteCarloOverlay;

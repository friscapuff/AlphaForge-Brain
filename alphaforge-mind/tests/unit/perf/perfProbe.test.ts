import { describe, it, expect } from 'vitest';
import { startProbe, measureProbe, flushProbe, aggregateProbe } from '../../../src/utils/perfProbe.js';

function busy(ms: number) { const end = performance.now() + ms; while (performance.now() < end) {/* spin */} }

describe('perfProbe', () => {
  it('captures manual start/stop', () => {
    const stop = startProbe('manual');
    busy(1);
    stop();
    const samples = flushProbe();
    const names = samples.map(s => s.name);
    expect(names).toContain('manual');
  });

  it('measureProbe wraps function', () => {
    measureProbe('wrapped', () => busy(1));
    const samples = flushProbe();
    expect(samples.some(s => s.name === 'wrapped' && (s.duration ?? 0) >= 0)).toBe(true);
  });

  it('aggregate produces stats', () => {
    for (let i=0;i<5;i++) measureProbe('agg', () => busy(0));
    const aggs = aggregateProbe();
    const agg = aggs.find(a => a.name === 'agg');
    expect(agg?.count).toBeGreaterThanOrEqual(5);
  });
});

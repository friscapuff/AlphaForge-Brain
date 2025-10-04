/** Timing utility tests (pre-T049). */
import { describe, it, expect } from 'vitest';
import { startTiming, withTiming, flushSpans } from '../../../src/services/api/timing.js';

function busyWait(ms: number) {
  const end = performance.now() + ms;
  while (performance.now() < end) {
    // spin
  }
}

describe('timing utility', () => {
  it('records span with start/stop', () => {
    const stop = startTiming('simple');
    stop();
    const spans = flushSpans();
    expect(spans.length).toBe(1);
    expect(spans[0].name).toBe('simple');
    expect(typeof spans[0].duration).toBe('number');
  });

  it('withTiming captures duration', () => {
    withTiming('block', () => busyWait(1));
    const spans = flushSpans();
  const span = spans.find((s) => s.name === 'block');
    expect(span).toBeTruthy();
    expect((span?.duration ?? 0)).toBeGreaterThanOrEqual(0);
  });

  it('separate spans maintain ordering', () => {
    const s1 = startTiming('a');
    const s2 = startTiming('b');
    s2();
    s1();
    const spans = flushSpans();
  const names = spans.map((s) => s.name);
    expect(names).toEqual(['a', 'b']);
  });
});

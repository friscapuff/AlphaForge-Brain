/**
 * perfProbe.ts (T053)
 * Lightweight performance probe utility to record named durations & paint metrics.
 */
export interface PerfSample { name: string; start: number; end?: number; duration?: number; meta?: Record<string, unknown>; }
export interface PerfAggregate { name: string; count: number; min: number; max: number; avg: number; p50: number; p95: number; }

class PerfProbe {
  private enabled = true;
  private samples: PerfSample[] = [];

  enable(v: boolean) { this.enabled = v; }

  start(name: string, meta?: Record<string, unknown>): () => void {
    if (!this.enabled) return () => undefined;
    const s: PerfSample = { name, start: performance.now(), meta };
    this.samples.push(s);
    return () => {
      if (s.end != null) return;
      s.end = performance.now();
      s.duration = s.end - s.start;
    };
  }

  measure<T>(name: string, fn: () => T, meta?: Record<string, unknown>): T {
    const stop = this.start(name, meta);
    try { return fn(); } finally { stop(); }
  }

  flush(): PerfSample[] { const out = this.samples.slice(); this.samples = []; return out; }

  aggregate(): PerfAggregate[] {
    const groups = new Map<string, number[]>();
    for (const s of this.samples) if (s.duration != null) {
      if (!groups.has(s.name)) groups.set(s.name, []);
      groups.get(s.name)!.push(s.duration);
    }
    const aggs: PerfAggregate[] = [];
    for (const [name, arr] of groups) {
      arr.sort((a,b)=>a-b);
      const count = arr.length;
      const sum = arr.reduce((p,c)=>p+c,0);
      const pct = (p: number) => arr[Math.min(arr.length-1, Math.floor(p*arr.length))];
      aggs.push({ name, count, min: arr[0], max: arr[arr.length-1], avg: sum/count, p50: pct(0.5), p95: pct(0.95) });
    }
    return aggs;
  }
}

export const perfProbe = new PerfProbe();
export const startProbe = (name: string, meta?: Record<string, unknown>) => perfProbe.start(name, meta);
export const measureProbe = <T>(name: string, fn: () => T, meta?: Record<string, unknown>) => perfProbe.measure(name, fn, meta);
export const flushProbe = () => perfProbe.flush();
export const aggregateProbe = () => perfProbe.aggregate();

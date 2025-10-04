import { describe, it, expect } from 'vitest';
import { canonicalJson } from '../../src/utils/canonicalJson.js';

/**
 * T096 Exported config JSON ordering & completeness test
 * Ensures deterministic key ordering and required top-level fields.
 */

describe('Export Config Determinism (T096)', () => {
  it('produces stable canonical JSON and required fields', () => {
    const sample = {
      runId: 'run_123',
      createdAt: '2025-09-27T00:00:00.000Z',
      strategy: { id: 'buy_hold', version: 'v1', params: [] },
      risk: { position_size_pct: 100, stop_type: 'none' }
    };
    const first = canonicalJson(sample);
    // Shuffle property insertion order
    const shuffled: any = { risk: sample.risk, strategy: sample.strategy, createdAt: sample.createdAt, runId: sample.runId };
    const second = canonicalJson(shuffled);
    expect(second).toEqual(first);
    const parsed = JSON.parse(first);
    expect(Object.keys(parsed)).toEqual(['createdAt','risk','runId','strategy']); // lexicographic order
    for (const k of ['runId','createdAt','strategy','risk']) {
      expect(parsed).toHaveProperty(k);
    }
  });
});

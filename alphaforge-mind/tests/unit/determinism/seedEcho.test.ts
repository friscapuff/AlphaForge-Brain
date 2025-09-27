/**
 * T026 Determinism seed echo test
 * Ensures given a fixed seed our lightweight random walk generator yields identical sequences.
 */
import { describe, it, expect } from 'vitest';
import { createLCG } from '../../../src/utils/random.js';

function lcgSequence(length: number, seed: number): number[] {
  const rng = createLCG(seed);
  const out: number[] = [];
  for (let i = 0; i < length; i++) out.push(rng.next());
  return out;
}

describe('T026 Seed determinism', () => {
  it('produces identical sequences for same seed', () => {
    const a = lcgSequence(20, 123456789);
    const b = lcgSequence(20, 123456789);
    expect(b).toEqual(a);
  });

  it('produces different sequences for different seed', () => {
    const a = lcgSequence(10, 111);
    const b = lcgSequence(10, 222);
    expect(b).not.toEqual(a);
  });
});

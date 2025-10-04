import { describe, it, expect } from 'vitest';
import { validateBacktestInput, canonicalizeBacktestInput } from '../../../src/utils/validation.js';

describe('validateBacktestInput', () => {
  it('accepts valid input', () => {
    const input = { start: '2020-01-01', end: '2020-12-31', strategy: 'meanReversion', equity: 10000 };
    const res = validateBacktestInput(input);
    expect(res.ok).toBe(true);
    expect(res.issues).toHaveLength(0);
  });

  it('flags missing fields and non-positive equity', () => {
    const res = validateBacktestInput({ start: '', end: '', strategy: '', equity: 0 });
    const fields = res.issues.map(i => i.field).sort();
    expect(fields).toEqual(['end', 'equity', 'start', 'strategy']);
    expect(res.ok).toBe(false);
  });

  it('parses string equity and canonicalizes', () => {
    const c = canonicalizeBacktestInput({ start: '2020-01-01', end: '2020-06-30', strategy: 's1', equity: '2500' });
    expect(typeof c.equity).toBe('number');
    expect(c.equity).toBe(2500);
  });
});

// T011 Date span validator tests
import { describe, it, expect } from 'vitest';

function validateDateSpan(start: string, end: string): { valid: boolean; warn?: string } {
  const s = new Date(start).getTime();
  const e = new Date(end).getTime();
  if (isNaN(s) || isNaN(e) || e < s) return { valid: false };
  const FIVE_YEARS_MS = 5 * 365 * 24 * 3600 * 1000;
  const span = e - s;
  if (span > FIVE_YEARS_MS) return { valid: true, warn: 'range-exceeds-5y' };
  return { valid: true };
}

describe('T011 date span validator', () => {
  it('rejects end before start', () => {
    expect(validateDateSpan('2024-01-02', '2024-01-01').valid).toBe(false);
  });
  it('warns if span exceeds 5 years', () => {
    const res = validateDateSpan('2015-01-01', '2024-02-01');
    expect(res.valid).toBe(true);
    expect(res.warn).toBe('range-exceeds-5y');
  });
  it('accepts normal range', () => {
    expect(validateDateSpan('2024-01-01', '2024-06-01').valid).toBe(true);
  });
});

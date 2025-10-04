import { describe, it, expect } from 'vitest';
import { resolveError, FALLBACK_ERROR } from '../../src/errors/errorMessages.js';

// Unit-level integration for mapping resolution logic (T094 UI side)

describe('errorMessages.resolveError', () => {
  it('maps exact known message', () => {
    const d = resolveError('run not found');
    expect(d.code).toBe('RUN_NOT_FOUND');
    expect(d.userMessage).toMatch(/could not be located/i);
  });

  it('maps prefix config error', () => {
    const d = resolveError('invalid configuration: some detail');
    expect(d.code).toBe('INVALID_CONFIG_PREFIX');
  });

  it('falls back on unknown', () => {
    const d = resolveError('totally new backend error');
    expect(d.code).toBe(FALLBACK_ERROR.code);
  });

  it('falls back on empty', () => {
    const d = resolveError('');
    expect(d.code).toBe(FALLBACK_ERROR.code);
  });
});

import * as v from 'vitest';

// Diagnostic: print what vitest resolves to in this environment
// eslint-disable-next-line no-console
console.log('vitest import keys:', v ? Object.keys(v).sort() : v);

const { it, expect, test, describe } = v as any;

// Also log types of common globals to verify injection
// eslint-disable-next-line no-console
console.log('typeof it:', typeof it, 'typeof test:', typeof test, 'typeof describe:', typeof describe);

it?.('sanity adds', () => {
  expect(1 + 1).toBe(2);
});

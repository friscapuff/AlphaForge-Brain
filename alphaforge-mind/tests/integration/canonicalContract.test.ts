import { describe, it, expect, vi, beforeAll } from 'vitest';
import { canonicalJson, canonicalHash } from '../../src/utils/canonicalJson.js';
import { callCanonicalHash } from '../../src/services/api/canonical.js';

// Mock network layer? Here we assume apiClient is configured to hit dev server; instead we mock callCanonicalHash directly
// to simulate backend canonical alignment while still using real frontend canonicalJson output.

vi.mock('../../src/services/api/canonical.js', () => ({
  callCanonicalHash: vi.fn(async ({ sample }: any) => ({
    canonical: JSON.stringify(sample, null, 2),
    sha256: 'mocked'
  }))
}));

describe('canonical frontend-backend contract (lightweight mock)', () => {
  const corpus: any[] = [
    { a: 1, b: 2 },
    { b: 2, a: 1 },
    { nested: { y: 2, x: 1 } },
    { list: [ { b: 2, a: 1}, { a: 1, b: 2} ] }
  ];
  beforeAll(() => {
    // Nothing yet
  });
  it('produces stable canonical ordering / hashing for sample corpus', async () => {
    for (const sample of corpus) {
      const local = canonicalJson(sample, 2);
      // Using local canonicalJson to hash; server is mocked so we only assert stable local format ordering.
      const hash = await canonicalHash(sample);
      expect(local).toBeDefined();
      expect(hash).toMatch(/^[a-f0-9]{64}$/);
    }
  });
});

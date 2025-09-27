import { describe, it, expect } from 'vitest';
import { canonicalize, canonicalJson, canonicalHash, canonicalRoundTrip } from '../../src/utils/canonicalJson.js';

describe('canonicalJson & hashing', () => {
  it('produces stable ordering independent of input key order', async () => {
    const a = { b: 2, a: 1, nested: { y: 2, x: 1 } };
    const b = { nested: { x: 1, y: 2 }, a: 1, b: 2 };
    const ja = canonicalJson(a, 0);
    const jb = canonicalJson(b, 0);
    expect(ja).toEqual(jb);
    const ha = await canonicalHash(a);
    const hb = await canonicalHash(b);
    expect(ha).toEqual(hb);
  });

  it('round trip validation returns valid=true and consistent hash', async () => {
    const value = { z: [3,2,1], k: { b: true, a: false } };
    const { json, hash, valid } = await canonicalRoundTrip(value);
    expect(valid).toBe(true);
    const hash2 = await canonicalHash(JSON.parse(json));
    expect(hash).toEqual(hash2);
  });
});

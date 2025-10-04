import { describe, it, expect, vi } from 'vitest';
import { afFetch, getResponseCorrelationId } from '../../src/net/client.js';

// Mock global fetch
const globalAny: any = global;

describe('afFetch correlation id propagation (Mind T095)', () => {
  it('injects provided correlation id', async () => {
    const echoHeaders: Record<string,string> = {};
    globalAny.fetch = vi.fn().mockResolvedValue({
      headers: new Map(Object.entries({ 'x-correlation-id': 'fixed-id-123' })),
      ok: true,
      status: 200,
      json: async () => ({}),
    });
    const r = await afFetch('https://example.test/api', { correlationId: 'abc-custom' });
    expect(globalAny.fetch).toHaveBeenCalled();
    // Check request header injection
    const callArgs = globalAny.fetch.mock.calls[0][1];
    const hdrs = callArgs.headers as Headers;
    expect(hdrs.get('x-correlation-id')).toBe('abc-custom');
    // Response correlation id should reflect server echo (fixed-id-123)
    expect(getResponseCorrelationId(r)).toBe('fixed-id-123');
  });

  it('generates correlation id when none provided', async () => {
    globalAny.fetch = vi.fn().mockResolvedValue({
      headers: new Map(),
      ok: true,
      status: 200,
      json: async () => ({}),
    });
    const r = await afFetch('https://example.test/other');
    const callArgs = globalAny.fetch.mock.calls[0][1];
    const hdrs = callArgs.headers as Headers;
    const sent = hdrs.get('x-correlation-id');
    expect(sent).toBeTruthy();
    expect(sent!.length).toBeGreaterThan(10);
    // No echo, so fallback retains generated id
    expect(getResponseCorrelationId(r)).toBe(sent);
  });
});

// T015 Monte Carlo default path count + percentile toggle logic
import { describe, it, expect } from 'vitest';

interface McOptions { requested?: number; extended?: boolean; }

function resolveMonteCarloConfig(opts: McOptions): { paths: number; needExtended: boolean } {
  const paths = opts.requested && opts.requested > 0 ? opts.requested : 200; // default
  const needExtended = !!opts.extended;
  return { paths, needExtended };
}

describe('T015 Monte Carlo config', () => {
  it('defaults to 200 when unspecified', () => {
    expect(resolveMonteCarloConfig({}).paths).toBe(200);
  });
  it('honors requested > 0', () => {
    expect(resolveMonteCarloConfig({ requested: 150 }).paths).toBe(150);
  });
  it('flags extended percentiles', () => {
    expect(resolveMonteCarloConfig({ extended: true }).needExtended).toBe(true);
  });
});

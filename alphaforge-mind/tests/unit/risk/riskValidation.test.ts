// T013 Risk config validation
import { describe, it, expect } from 'vitest';

interface RiskConfig { position_sizing: 'fixed_fraction'|'fixed_amount'; fraction?: number; amount?: number; }

function validateRisk(cfg: RiskConfig): { ok: boolean; error?: string } {
  if (cfg.position_sizing === 'fixed_fraction') {
    if (typeof cfg.fraction !== 'number' || cfg.fraction <= 0 || cfg.fraction > 1) return { ok: false, error: 'fraction-range' };
  } else if (cfg.position_sizing === 'fixed_amount') {
    if (typeof cfg.amount !== 'number' || cfg.amount <= 0) return { ok: false, error: 'amount-invalid' };
  } else return { ok: false, error: 'mode-unknown' };
  return { ok: true };
}

describe('T013 risk config validation', () => {
  it('accepts valid fraction', () => {
    expect(validateRisk({ position_sizing: 'fixed_fraction', fraction: 0.2 }).ok).toBe(true);
  });
  it('rejects invalid fraction', () => {
    expect(validateRisk({ position_sizing: 'fixed_fraction', fraction: 2 }).error).toBe('fraction-range');
  });
  it('accepts amount mode', () => {
    expect(validateRisk({ position_sizing: 'fixed_amount', amount: 5000 }).ok).toBe(true);
  });
  it('rejects missing amount', () => {
    expect(validateRisk({ position_sizing: 'fixed_amount' }).error).toBe('amount-invalid');
  });
});

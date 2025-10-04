// T012 Strategy param coercion & bounds
import { describe, it, expect } from 'vitest';

interface ParamDef { name: string; type: 'int'|'float'; min?: number; max?: number; }

function coerceParams(raw: Record<string, unknown>, defs: ParamDef[]): Record<string, number> {
  const out: Record<string, number> = {};
  for (const d of defs) {
    let v = raw[d.name];
    if (v == null) throw new Error(`missing ${d.name}`);
    if (d.type === 'int') v = parseInt(String(v), 10);
    else v = parseFloat(String(v));
    if (Number.isNaN(v)) throw new Error(`invalid number for ${d.name}`);
    if (d.min != null && (v as number) < d.min) throw new Error(`${d.name} < min`);
    if (d.max != null && (v as number) > d.max) throw new Error(`${d.name} > max`);
    out[d.name] = v as number;
  }
  return out;
}

describe('T012 strategy param coercion', () => {
  const defs: ParamDef[] = [
    { name: 'fast', type: 'int', min: 1, max: 50 },
    { name: 'slow', type: 'int', min: 5, max: 250 },
  ];
  it('coerces string numbers', () => {
    const r = coerceParams({ fast: '12', slow: '100' }, defs);
    expect(r.fast).toBe(12);
    expect(r.slow).toBe(100);
  });
  it('enforces bounds', () => {
    expect(() => coerceParams({ fast: 0, slow: 10 }, defs)).toThrow('fast < min');
    expect(() => coerceParams({ fast: 10, slow: 5000 }, defs)).toThrow('slow > max');
  });
  it('errors on missing', () => {
    expect(() => coerceParams({ fast: 10 }, defs)).toThrow('missing slow');
  });
});

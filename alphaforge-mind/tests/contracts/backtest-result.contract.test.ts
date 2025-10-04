import { describe, it, expect } from 'vitest';
// Ajv ESM default import type quirk under NodeNext & strict TS: import as * then cast
import Ajv2 from 'ajv';
import * as fs from 'node:fs';
import * as path from 'node:path';
import addFormatsModule from 'ajv-formats';

// Cast to any to construct (avoids constructor signature mismatch with types under NodeNext)
const Ajv: any = Ajv2 as any;
const ajv = new Ajv({ allErrors: true, strict: false });
const addFormats: any = (addFormatsModule as any).default || (addFormatsModule as any);
addFormats(ajv);

function loadSchema(name: string) {
  const p = path.resolve(__dirname, '../../../specs/006-begin-work-on/contracts', name);
  return JSON.parse(fs.readFileSync(p, 'utf-8'));
}

describe('T008 Backtest result payload contract', () => {
  const schema = loadSchema('backtest-result.v1.schema.json');
  const validate = ajv.compile(schema);
  it('accepts valid result payload', () => {
    const t0 = Date.now() - 60000;
    const payload = {
      run_id: 'bt_123',
      metrics: { cagr: 0.12, sharpe: 1.4 },
      equity: [ { t: t0, equity: 10000 }, { t: t0 + 60000, equity: 10025 } ],
      trades_summary: { count: 10, win_rate: 0.5 },
      validation: { bootstrap: {}, permutation: {}, walk_forward: {} }
    } as any; // loosen for schema fields only
    const ok = validate(payload);
    if (!ok) console.error(validate.errors);
    expect(ok).toBe(true);
  });
});

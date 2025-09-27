import { describe, it, expect } from 'vitest';
import Ajv2 from 'ajv';
import addFormatsModule from 'ajv-formats';
import * as fs from 'node:fs';
import * as path from 'node:path';

const Ajv: any = Ajv2 as any;
const ajv = new Ajv({ allErrors: true, strict: false });
const addFormats: any = (addFormatsModule as any).default || (addFormatsModule as any);
addFormats(ajv);

function loadSchema(name: string) {
  const p = path.resolve(__dirname, '../../../specs/006-begin-work-on/contracts', name);
  return JSON.parse(fs.readFileSync(p, 'utf-8'));
}

describe('T007 Backtest run request contract', () => {
  const schema = loadSchema('backtest-run-request.v1.schema.json');
  const validate = ajv.compile(schema);
  it('accepts valid payload', () => {
    const payload = {
      date_from: new Date(Date.now() - 86400000 * 30).toISOString(),
      date_to: new Date().toISOString(),
      ticker: 'AAPL',
      strategy: {
        strategy_id: 'ema_cross',
        params: [
          { name: 'fast', value: 12, type: 'int', min: 1, max: 50 },
          { name: 'slow', value: 26, type: 'int', min: 10, max: 200 },
        ],
        version: '1.0.0',
      },
      risk: { position_size_pct: 10, stop_type: 'percent', stop_value: 2 },
      validation: { bootstrap: false, permutation: false, walkforward: false, montecarlo: false },
    };
    const ok = validate(payload);
    if (!ok) console.error(validate.errors);
    expect(ok).toBe(true);
  });
});

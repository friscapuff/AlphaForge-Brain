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

describe('T006 Candles contract', () => {
  const schema = loadSchema('chart-candles.v1.schema.json');
  const validate = ajv.compile(schema);
  it('accepts valid minimal payload', () => {
    const now = new Date();
    const payload = {
      symbol: 'AAPL',
      interval: '1d',
      from: new Date(now.getTime() - 86400000).toISOString(),
      to: now.toISOString(),
      candles: [
        { t: Date.now() - 60000, o: 100.1, h: 101.2, l: 99.9, c: 100.5, v: 12345 },
      ],
    };
    const ok = validate(payload);
    if (!ok) {
      // Helpful debug output
      console.error(validate.errors);
    }
    expect(ok).toBe(true);
  });
});

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

describe('T009 Monte Carlo paths payload contract', () => {
  const schema = loadSchema('montecarlo-paths.v1.schema.json');
  const validate = ajv.compile(schema);
  it('accepts valid payload', () => {
    const makePoints = () => [
      { t: Date.now(), equity: 10000 },
      { t: Date.now() + 1000, equity: 10010 },
    ];
    const payload = {
      run_id: 'bt_123',
      seed: '987654321',
      paths: [ { path_id: 0, points: makePoints() }, { path_id: 1, points: makePoints() } ],
      p5: makePoints(),
      p95: makePoints(),
    };
    const ok = validate(payload);
    if (!ok) console.error(validate.errors);
    expect(ok).toBe(true);
  });
});

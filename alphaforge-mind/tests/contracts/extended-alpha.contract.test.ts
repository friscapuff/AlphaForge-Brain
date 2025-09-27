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

describe('T010 Extended alpha2 Monte Carlo contract', () => {
  const schema = loadSchema('montecarlo-paths.v1alpha2.schema.json');
  const validate = ajv.compile(schema);
  it('accepts payload with extended percentiles', () => {
    const mk = () => [ { t: Date.now(), equity: 10000 }, { t: Date.now() + 500, equity: 10005 } ];
    const payload = {
      run_id: 'bt_123',
      seed: '111',
      paths: [ { path_id: 0, points: mk() } ],
      p5: mk(),
      p95: mk(),
      extended: {
        p1: mk(),
        p50: mk(),
        p99: mk()
      }
    };
    const ok = validate(payload);
    if (!ok) console.error(validate.errors);
    expect(ok).toBe(true);
  });
});

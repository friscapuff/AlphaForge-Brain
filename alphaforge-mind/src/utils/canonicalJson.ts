/**
 * canonicalJson
 * Produces a deterministic JSON string with sorted object keys (deep) and stable primitive formatting.
 * Arrays preserve order; objects sorted lexicographically by key.
 */
export function canonicalize(value: any): any {
  if (value === null || typeof value !== 'object') return value;
  if (Array.isArray(value)) return value.map(v => canonicalize(v));
  const out: Record<string, any> = {};
  for (const key of Object.keys(value).sort()) {
    out[key] = canonicalize(value[key]);
  }
  return out;
}

export function canonicalJson(value: any, space = 2): string {
  const canon = canonicalize(value);
  return JSON.stringify(canon, null, space);
}

/** Compute a stable SHA-256 hash of the canonical JSON (hex lowercase). */
export async function canonicalHash(value: any): Promise<string> {
  const data = new TextEncoder().encode(canonicalJson(value, 0));
  // Browser / Web Crypto path
  if (typeof crypto !== 'undefined' && (crypto as any).subtle) {
    const digest = await (crypto as any).subtle.digest('SHA-256', data);
    return Array.from(new Uint8Array(digest)).map(b => b.toString(16).padStart(2, '0')).join('');
  }
  // Node fallback
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const nodeCrypto = require('crypto');
    return nodeCrypto.createHash('sha256').update(data).digest('hex');
  } catch {
    throw new Error('No crypto available for hashing');
  }
}

/** Round trip validator: stringify -> parse -> re-canonicalize, ensuring stability. */
export async function canonicalRoundTrip(value: any): Promise<{ json: string; hash: string; valid: boolean }> {
  const json = canonicalJson(value, 2);
  const parsed = JSON.parse(json);
  const json2 = canonicalJson(parsed, 2);
  const valid = json === json2;
  const hash = await canonicalHash(value);
  return { json, hash, valid };
}

export default canonicalJson;

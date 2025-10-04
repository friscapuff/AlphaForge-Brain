// Lightweight fetch wrapper injecting correlation id header (T095 Mind side)
import { handleErrorResponse } from './errors.js';
// Lightweight RFC4122-ish id (not cryptographically strong) to avoid external dependency in test env
function uuidv4(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export interface RequestOptions extends RequestInit {
  correlationId?: string;
}

export async function afFetch(url: string, opts: RequestOptions = {}): Promise<Response> {
  const cid = opts.correlationId || uuidv4();
  const headers = new Headers(opts.headers || {});
  headers.set('x-correlation-id', cid);
  const resp = await fetch(url, { ...opts, headers });
  // Echo header may differ if backend overwrites; capture for chaining if needed
  (resp as any)._correlationId = resp.headers.get('x-correlation-id') || cid;
  if (!resp.ok) {
    // Fire and forget; store updated for banner consumption
    try { await handleErrorResponse(resp.clone()); } catch { /* noop */ }
  }
  return resp;
}

export function getResponseCorrelationId(resp: Response): string | undefined {
  return (resp as any)._correlationId;
}

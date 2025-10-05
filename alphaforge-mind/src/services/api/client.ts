/**
 * API Client Wrapper (T027)
 * - Provides JSON fetch with error normalization
 * - Attaches optional correlation headers (future T048/T049 extension)
 * - Handles base URL from VITE_API_BASE_URL or fallback
 */

export interface ApiErrorShape {
  status: number;
  message: string;
  code?: string;
  details?: unknown;
}

export class ApiError extends Error implements ApiErrorShape {
  status: number;
  code?: string;
  details?: unknown;
  constructor(err: ApiErrorShape) {
    super(err.message);
    this.status = err.status;
    this.code = err.code;
    this.details = err.details;
  }
}

import { startTiming } from './timing.js';

interface RequestOptions extends RequestInit {
  query?: Record<string, string | number | boolean | undefined>;
  headers?: Record<string, string>;
}

function buildUrl(base: string, path: string, query?: RequestOptions['query']) {
  const url = new URL(path.replace(/^\//, ''), base.endsWith('/') ? base : base + '/');
  if (query) {
    Object.entries(query).forEach(([k, v]) => {
      if (v === undefined) return;
      url.searchParams.set(k, String(v));
    });
  }
  return url.toString();
}

export class ApiClient {
  readonly baseUrl: string;
  // Cast import.meta to any to avoid NodeNext typing friction without a full vite env shim during tests
  constructor(baseUrl = (import.meta as any)?.env?.VITE_API_BASE_URL || 'http://localhost:8000/api/v1/') {
    this.baseUrl = baseUrl;
  }

  async json<T = unknown>(path: string, opts: RequestOptions = {}): Promise<T> {
    const { query, headers, ...init } = opts;
    const url = buildUrl(this.baseUrl, path, query);
    const stop = startTiming('api.fetch', { path, url });
    const resp = await fetch(url, {
      ...init,
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        ...(headers || {}),
      },
    });

    const text = await resp.text();
    let payload: any = undefined;
    try {
      payload = text ? JSON.parse(text) : undefined;
    } catch {
      /* non JSON fallback */
    }

    if (!resp.ok) {
      stop();
      const normalized: ApiErrorShape = {
        status: resp.status,
        message: payload?.message || resp.statusText || 'Request failed',
        code: payload?.code,
        details: payload?.details ?? payload,
      };
      throw new ApiError(normalized);
    }
    stop();
    return payload as T;
  }
}

export const apiClient = new ApiClient();

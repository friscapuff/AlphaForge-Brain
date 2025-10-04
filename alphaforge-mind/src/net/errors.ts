import { resolveError, FALLBACK_ERROR, ERROR_MAP } from '../errors/errorMessages.js';
import { useErrorStore } from '../state/errors.js';
import { getResponseCorrelationId } from './client.js';

// Helper to extract structured backend error envelope
interface BackendErrorEnvelope {
  detail?: string;
  error?: { code?: string; message?: string; retryable?: boolean };
}

export async function handleErrorResponse(resp: Response): Promise<void> {
  let payload: BackendErrorEnvelope | undefined;
  try {
    payload = await resp.json();
  } catch {
    // Not JSON – synthesize a fallback detail
    payload = { detail: `HTTP ${resp.status}` };
  }
  const correlationId = getResponseCorrelationId(resp);
  const resetAfterHeader = resp.headers.get('x-rate-limit-reset-after');
  const resetAfterSec = resetAfterHeader ? parseInt(resetAfterHeader, 10) : undefined;
  const descriptor = resolveError(payload?.detail || payload?.error?.code || payload?.error?.message);
  useErrorStore.getState().setError({
    descriptor: descriptor || FALLBACK_ERROR,
    correlationId,
    rateLimitResetMs: resetAfterSec ? Date.now() + resetAfterSec * 1000 : undefined,
    retryable: payload?.error?.retryable,
    rawDetail: payload?.detail || payload?.error?.message,
  });
}

export function clearError(): void {
  useErrorStore.getState().clear();
}

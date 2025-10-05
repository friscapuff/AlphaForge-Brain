import { apiClient } from './client.js';

export interface CanonicalHashResponse {
  canonical: string;
  sha256: string;
}

/**
 * callCanonicalHash
 * Posts an arbitrary payload to the backend canonicalization endpoint and returns
 * the canonical JSON string + stable sha256 hash produced server-side.
 *
 * Throws ApiError on non-2xx just like apiClient.json.
 */
export async function callCanonicalHash(payload: unknown): Promise<CanonicalHashResponse> {
  return apiClient.json<CanonicalHashResponse>('/canonical/hash', {
    method: 'POST',
    body: JSON.stringify({ payload }),
  });
}

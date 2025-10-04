/**
 * useCandles (T030)
 * Fetches candle data via ApiClient + React Query.
 * - Accepts symbol & range (range currently passed-through as query param)
 * - Normalizes output into Candle[] (shared with store)
 */
import { useQuery, UseQueryResult } from '@tanstack/react-query';
import { apiClient } from '../services/api/client.js';
import type { Candle } from '../state/store.js';

export interface CandlesResponse {
  symbol: string;
  interval?: string;
  candles: Array<{ t: string; o: number; h: number; l: number; c: number; v: number }>;
}

export function useCandles(symbol: string, range: string): UseQueryResult<Candle[], unknown> {
  // For now, map range to interval heuristically (placeholder logic)
  const interval = range === '1M' ? '1d' : '1h';
  return useQuery({
    queryKey: ['candles', symbol, range],
    queryFn: async () => {
      const data = await apiClient.json<CandlesResponse>(`/market/candles`, {
        query: { symbol, interval },
      });
      return data.candles.map((c) => ({ ...c }));
    },
    staleTime: 30_000,
  });
}

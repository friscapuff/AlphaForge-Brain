import { useQuery, UseQueryResult } from '@tanstack/react-query';
import { fetchTrustGateMetrics, TrustGateMetrics } from '../services/metrics/trustGates.js';

export function useTrustGateMetrics(enabled = true): UseQueryResult<TrustGateMetrics, unknown> {
  return useQuery({
    queryKey: ['trust-gate-metrics'],
    queryFn: fetchTrustGateMetrics,
    refetchInterval: enabled ? 30_000 : false,
    refetchOnWindowFocus: enabled,
    staleTime: 15_000,
    enabled,
  });
}

import React from 'react';
import { useTrustGateMetrics } from '../../hooks/useTrustGateMetrics.js';

export function TrustGateAlertToast(): React.ReactElement | null {
  const { data } = useTrustGateMetrics();
  const failing = data?.gates.filter((gate) => !gate.healthy) ?? [];
  if (!data || failing.length === 0) {
    return null;
  }

  return (
    <div
      role="alert"
      className="fixed bottom-4 left-4 right-4 z-40 mx-auto max-w-3xl rounded border border-red-800 bg-red-950/70 p-4 text-sm text-red-100 shadow-xl backdrop-blur"
    >
      <p className="font-semibold tracking-wide">Trust gate failure detected</p>
      <p className="mt-1 text-xs text-red-100/80">
        {failing.map((gate) => gate.name).join(', ')} reporting unhealthy status via Prometheus. Investigate diagnostics under
        <code className="mx-1 rounded bg-red-900/70 px-1 py-0.5 text-[11px]">artifacts/trust_gates/reports/</code> and ensure waivers are up to date.
      </p>
      <p className="mt-2 text-[11px] text-red-100/70">Metrics refreshed {data.collectedAt.toLocaleTimeString()} · persists until gates report healthy.</p>
    </div>
  );
}

export default TrustGateAlertToast;

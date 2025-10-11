import React from 'react';
import { useTrustGateMetrics } from '../../hooks/useTrustGateMetrics.js';

const DOCS_URL = (import.meta as any)?.env?.VITE_TRUST_GATES_DOCS_URL ?? 'https://docs.internal.alphaforge/trust-gates';

function formatMs(value?: number): string {
  if (value === undefined || Number.isNaN(value)) return '—';
  if (value >= 1000) {
    return `${(value / 1000).toFixed(2)} s`;
  }
  return `${value.toFixed(0)} ms`;
}

function formatTimestamp(date?: Date): string {
  if (!date) return '—';
  const now = Date.now();
  const diff = now - date.getTime();
  if (diff < 60_000) return 'just now';
  if (diff < 3_600_000) return `${Math.round(diff / 60_000)} min ago`;
  return date.toLocaleString();
}

export function TrustGatePanel(): React.ReactElement {
  const { data, isLoading, isError, error, refetch, isFetching } = useTrustGateMetrics();
  const gates = data?.gates ?? [];
  const failing = gates.filter((gate) => !gate.healthy);
  const updatedAt = data?.collectedAt;

  return (
    <section aria-labelledby="trust-gate-panel-title" className="rounded-lg border border-neutral-800 bg-neutral-900 p-4 shadow-sm space-y-4">
      <header className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 id="trust-gate-panel-title" className="text-lg font-semibold text-neutral-100">Trust Gate Health</h2>
          <p className="text-xs text-neutral-400">Live Prometheus metrics, refreshed every 30&nbsp;seconds.</p>
        </div>
        <button
          type="button"
          onClick={() => void refetch()}
          className="self-start rounded border border-neutral-700 bg-neutral-800 px-3 py-1 text-xs text-neutral-200 hover:bg-neutral-700"
          aria-busy={isFetching}
        >
          {isFetching ? 'Refreshing…' : 'Refresh now'}
        </button>
      </header>

      {isLoading && (
        <p className="text-sm text-neutral-300" role="status">Loading trust gate metrics…</p>
      )}

      {isError && (
        <div role="alert" className="rounded border border-red-800 bg-red-950/40 p-3 text-sm text-red-200">
          Unable to load Prometheus metrics. {error instanceof Error ? error.message : 'Check the metrics endpoint configuration.'}
        </div>
      )}

      {!isLoading && !isError && gates.length === 0 && (
        <div className="rounded border border-amber-800 bg-amber-950/40 p-3 text-sm text-amber-200" role="alert">
          No trust gate metrics available. Verify that the Prometheus scrape job exposes `trust_gate_*` series.
        </div>
      )}

      {gates.length > 0 && (
        <>
          {failing.length > 0 ? (
            <div className="rounded border border-red-800 bg-red-950/40 p-3 text-sm text-red-200" role="alert">
              <p className="font-semibold">Attention required</p>
              <p className="text-xs text-red-200/80">
                {failing.length} gate{failing.length === 1 ? '' : 's'} reporting failures: {failing.map((gate) => gate.name).join(', ')}. Review trust gate diagnostics and waivers.
              </p>
            </div>
          ) : (
            <div className="rounded border border-emerald-800 bg-emerald-950/30 p-3 text-sm text-emerald-200" role="status">
              All trust gates are healthy.
            </div>
          )}

          <div className="overflow-x-auto">
            <table className="min-w-full table-fixed border-collapse text-left text-xs text-neutral-200">
              <thead>
                <tr className="text-neutral-400">
                  <th scope="col" className="border-b border-neutral-800 px-3 py-2 w-32">Gate</th>
                  <th scope="col" className="border-b border-neutral-800 px-3 py-2 w-24">Status</th>
                  <th scope="col" className="border-b border-neutral-800 px-3 py-2 w-24">Failures</th>
                  <th scope="col" className="border-b border-neutral-800 px-3 py-2">Mean runtime</th>
                </tr>
              </thead>
              <tbody>
                {gates.map((gate) => (
                  <tr key={gate.name} className="odd:bg-neutral-900/60">
                    <th scope="row" className="px-3 py-2 font-medium text-neutral-100">{gate.name}</th>
                    <td className="px-3 py-2">
                      <span
                        className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-[11px] ${gate.healthy ? 'bg-emerald-900/60 text-emerald-200 border border-emerald-700' : 'bg-red-900/60 text-red-200 border border-red-700'}`}
                      >
                        {gate.healthy ? 'pass' : 'fail'}
                      </span>
                    </td>
                    <td className="px-3 py-2">{gate.failureCount}</td>
                    <td className="px-3 py-2">{formatMs(gate.meanDurationMs)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <footer className="flex flex-col gap-2 text-xs text-neutral-500 sm:flex-row sm:items-center sm:justify-between">
            <span>Last updated: {formatTimestamp(updatedAt)}</span>
            <a
              href={DOCS_URL}
              className="text-neutral-300 underline-offset-2 hover:underline"
              target="_blank"
              rel="noreferrer"
            >
              Read the trust gate runbook
            </a>
          </footer>
        </>
      )}
    </section>
  );
}

export default TrustGatePanel;

import React, { useMemo } from 'react';
import type { ApiTrustGateSummary, TrustGateResult, TrustGateSummary } from '../services/api/backtests.js';
import { mapTrustGateSummary } from '../services/api/backtests.js';

interface TrustGateBadgeProps {
  suite?: TrustGateSummary | ApiTrustGateSummary | null;
  className?: string;
}

type SummaryMeta = {
  className: string;
  label: string;
  icon: string;
};

function normalizeSummary(suite?: TrustGateSummary | ApiTrustGateSummary | null): TrustGateSummary | undefined {
  if (!suite) return undefined;
  if (typeof suite === 'object' && ('suite_version' in suite || 'executed_at' in suite || 'schema_version' in suite)) {
    return mapTrustGateSummary(suite as ApiTrustGateSummary) ?? undefined;
  }
  return suite as TrustGateSummary;
}

function deriveSummaryMeta(summary?: TrustGateSummary): SummaryMeta {
  if (!summary) {
    return {
      className: 'bg-neutral-900/60 border-neutral-700 text-neutral-300',
      icon: '…',
      label: 'trust gates pending',
    };
  }

  const normalizedStatus = (summary.status ?? 'unknown').toLowerCase();
  const hasFail = summary.gates.some((gate) => gate.status.toLowerCase() === 'fail');
  const hasWarn = summary.gates.some((gate) => gate.status.toLowerCase() === 'warn');
  const hasWaiver = summary.gates.some((gate) => Boolean(gate.waiverRef));

  if (hasFail || normalizedStatus === 'fail') {
    return {
      className: 'bg-rose-900/40 border-rose-700 text-rose-200',
      icon: '✕',
      label: 'trust gates fail',
    };
  }

  if (hasWarn || normalizedStatus === 'warn') {
    return {
      className: 'bg-amber-900/40 border-amber-700 text-amber-200',
      icon: '⚠',
      label: 'trust gates warning',
    };
  }

  if (hasWaiver) {
    return {
      className: 'bg-sky-900/40 border-sky-700 text-sky-200',
      icon: '⚑',
      label: 'trust gates waived',
    };
  }

  if (normalizedStatus === 'pass') {
    return {
      className: 'bg-emerald-900/40 border-emerald-700 text-emerald-200',
      icon: '✓',
      label: 'trust gates pass',
    };
  }

  return {
    className: 'bg-neutral-900/60 border-neutral-700 text-neutral-300',
    icon: '…',
    label: 'trust gates pending',
  };
}

function formatRuntime(runtimeMs?: number): string | undefined {
  if (typeof runtimeMs !== 'number' || Number.isNaN(runtimeMs)) return undefined;
  if (runtimeMs < 1000) {
    return `${runtimeMs} ms`;
  }
  const seconds = runtimeMs / 1000;
  if (seconds >= 120) {
    return `${(seconds / 60).toFixed(1)} min`;
  }
  return `${seconds.toFixed(seconds >= 10 ? 1 : 2)} s`;
}

function GateRow({ gate }: { gate: TrustGateResult }) {
  const statusLower = gate.status.toLowerCase();
  let statusClass = 'bg-neutral-900/60 border-neutral-700 text-neutral-300';
  if (statusLower === 'pass') {
    statusClass = 'bg-emerald-900/40 border-emerald-700 text-emerald-200';
  } else if (statusLower === 'fail') {
    statusClass = 'bg-rose-900/40 border-rose-700 text-rose-200';
  } else if (statusLower === 'warn' || statusLower === 'warning') {
    statusClass = 'bg-amber-900/40 border-amber-700 text-amber-200';
  }
  const gateRuntime = formatRuntime(gate.durationMs);

  return (
    <li className="border border-neutral-700 rounded p-2 space-y-1" data-testid={`trust-gate-${gate.name}`}>
      <div className="flex flex-wrap items-center gap-2 text-[11px] text-neutral-100">
        <span className="font-semibold text-neutral-200">{gate.name}</span>
        <span
          className={`px-1.5 py-0.5 text-[10px] rounded-full border ${statusClass}`}
          aria-label={`status ${gate.status}`}
        >
          {gate.status.toUpperCase()}
        </span>
        {gate.waiverRef && (
          <span className="text-[10px] text-sky-300" title="Gate has active waiver">
            waiver {gate.waiverRef}
          </span>
        )}
        {gateRuntime && (
          <span className="ml-auto text-[10px] text-neutral-500">
            runtime {gateRuntime}
          </span>
        )}
      </div>
      <div className="grid grid-cols-[auto_1fr] gap-x-2 gap-y-1 text-[10px] text-neutral-400">
        <span>correlation</span>
        <span className="font-mono text-[10px] text-neutral-200 break-all">
          {gate.correlationId ?? '—'}
        </span>
        {gate.artifact && (
          <>
            <span>artifact</span>
            <a
              href={`#/artifacts/${encodeURIComponent(gate.artifact)}`}
              className="text-sky-300 underline"
            >
              {gate.artifact}
            </a>
          </>
        )}
      </div>
      {gate.details && (
        <p className="text-[10px] text-neutral-300">{gate.details}</p>
      )}
      {gate.metrics && (
        <pre className="mt-1 text-[10px] bg-neutral-900/60 border border-neutral-800 rounded p-1 text-neutral-300 overflow-auto max-h-32">
          {JSON.stringify(gate.metrics, null, 2)}
        </pre>
      )}
      {gate.tolerance && (
        <pre className="mt-1 text-[10px] bg-neutral-900/60 border border-neutral-800 rounded p-1 text-neutral-300 overflow-auto max-h-32">
          {JSON.stringify(gate.tolerance, null, 2)}
        </pre>
      )}
    </li>
  );
}

export function TrustGateBadge({ suite, className }: TrustGateBadgeProps): React.ReactElement {
  const summary = useMemo(() => normalizeSummary(suite), [suite]);
  const meta = deriveSummaryMeta(summary);
  const runtimeLabel = formatRuntime(summary?.runtimeMs);

  if (!summary) {
    return (
      <section className={`text-xs text-neutral-500 border border-neutral-700 rounded p-2 ${className ?? ''}`} data-testid="trust-gate-badge">
        Trust gate results pending.
      </section>
    );
  }

  return (
    <section className={`text-xs border border-neutral-700 rounded p-3 space-y-2 bg-neutral-950/40 ${className ?? ''}`} data-testid="trust-gate-badge">
      <header className="flex flex-wrap items-center gap-2">
        <span className={`px-2 py-0.5 rounded-full border ${meta.className}`} data-testid="trust-gate-status">
          {meta.icon} {meta.label}
          {summary.status && <span className="sr-only">{summary.status}</span>}
        </span>
        {summary.executedAt && (
          <span className="text-[10px] text-neutral-400" title="Execution timestamp">
            executed {summary.executedAt}
          </span>
        )}
        {runtimeLabel && (
          <span className="text-[10px] text-neutral-500">total runtime {runtimeLabel}</span>
        )}
        {summary.toleranceProfile && (
          <span className="text-[10px] text-neutral-500">profile {summary.toleranceProfile}</span>
        )}
        {summary.signaturePath && (
          <a
            href={`#/artifacts/${encodeURIComponent(summary.signaturePath)}`}
            className="text-[10px] text-sky-300 underline"
          >
            signature
          </a>
        )}
      </header>
      <ul className="grid gap-2" aria-label="Trust gate statuses">
        {summary.gates.length === 0 ? (
          <li className="text-[11px] text-neutral-500">No gates reported.</li>
        ) : (
          summary.gates.map((gate) => <GateRow key={`${gate.name}-${gate.correlationId ?? 'na'}`} gate={gate} />)
        )}
      </ul>
    </section>
  );
}

export default TrustGateBadge;

import React from 'react';
import type {
  ValidationData,
  PermutationSegment,
  ValidationStatus,
  ValidationConfigModule,
  CrossValidationSection,
  ExecutionRealismSection,
  BiasAdjustments,
  ValidationArtifact,
} from '../../services/api/backtests.js';

interface ValidationOutputsProps {
  validation?: ValidationData;
  runId?: string;
  cautionMetrics?: string[];
}

export function ValidationOutputs({ validation, runId, cautionMetrics = [] }: ValidationOutputsProps) {
  if (!validation) {
    return (
      <div className="text-xs text-neutral-500 border border-neutral-700 rounded p-2" data-testid="validation-empty">
        No validation payload has been received for this run yet.
      </div>
    );
  }

  const {
    significanceStatus,
    config,
    permutation,
    biasAdjustments,
    crossValidation,
    executionRealism,
    failedChecks,
    cautionChecks,
    metadata,
    manifestHash,
    artifacts,
  } = validation;

  return (
    <section className="flex flex-col gap-3 text-xs" aria-label="Validation outputs" data-testid="validation-outputs">
      <header className="flex flex-wrap items-center gap-2 text-sm font-medium">
        <span>Validation significance</span>
        <StatusBadge status={significanceStatus} />
        {typeof config.significanceThreshold === 'number' && (
          <span className="text-[11px] text-neutral-400">
            Threshold p ≤ {config.significanceThreshold.toFixed(3)}
          </span>
        )}
        {(typeof config.biasAbsoluteThreshold === 'number' || typeof config.biasRelativeThreshold === 'number') && (
          <span className="text-[11px] text-neutral-400 flex items-center gap-1">
            Bias thresholds
            <span className="text-neutral-500">
              abs {formatNumber(config.biasAbsoluteThreshold)} · rel {formatNumber(config.biasRelativeThreshold)}
            </span>
          </span>
        )}
        {runId && (
          <span className="ml-auto text-[11px] text-neutral-500" data-testid="validation-run-id">
            Run: {runId}
          </span>
        )}
      </header>

      {manifestHash && (
        <div className="text-[11px] text-neutral-400 font-mono" data-testid="validation-manifest-hash">
          Manifest hash: <span className="break-all text-neutral-200">{manifestHash}</span>
        </div>
      )}

      {cautionMetrics.length > 0 && (
        <div
          className="bg-amber-900/30 border border-amber-700 text-amber-200 px-2 py-1 rounded text-[11px]"
          data-testid="validation-caution-metrics"
        >
          <span className="font-semibold mr-2">Caution signals:</span>
          <span>{cautionMetrics.join(', ')}</span>
        </div>
      )}

      <ModulesList modules={config.modules} />

      <div className="grid gap-3 md:grid-cols-2">
        <SignalsCard failedChecks={failedChecks} cautionChecks={cautionChecks} />
        <PermutationCard
          segments={permutation?.segments ?? []}
          significanceThreshold={config.significanceThreshold}
        />
        <BiasAdjustmentsCard data={biasAdjustments} />
        <CrossValidationCard
          data={crossValidation}
          leakageThreshold={config.leakageThreshold}
        />
        <ExecutionRealismCard
          data={executionRealism}
          capacityLimitBps={config.realismCapacityBpsLimit}
        />
        <MetadataCard metadata={metadata} />
        <ArtifactsCard artifacts={artifacts} />
      </div>
    </section>
  );
}

export default ValidationOutputs;

// ----- Status Badge -----
function StatusBadge({ status }: { status: ValidationStatus }) {
  const { className, label } = getStatusMeta(status);
  return (
    <span className={`px-2 py-0.5 text-[11px] rounded-full border ${className}`} data-testid="validation-status-badge">
      {label}
    </span>
  );
}

function getStatusMeta(status: ValidationStatus): { className: string; label: string } {
  switch (status) {
    case 'pass':
      return { className: 'bg-emerald-900/40 border-emerald-700 text-emerald-300', label: 'pass' };
    case 'caution':
      return { className: 'bg-amber-900/40 border-amber-700 text-amber-300', label: 'caution' };
    case 'fail':
      return { className: 'bg-rose-900/40 border-rose-700 text-rose-300', label: 'fail' };
    default:
      return { className: 'bg-neutral-800 border-neutral-600 text-neutral-300', label: 'pending' };
  }
}

// ----- Modules List -----
function ModulesList({ modules }: { modules: ValidationConfigModule[] }) {
  if (!modules.length) {
    return (
      <div className="border border-neutral-700 rounded p-2 text-[11px] text-neutral-500">
        No validation modules reported.
      </div>
    );
  }
  return (
    <div className="border border-neutral-700 rounded p-2" aria-label="Validation modules">
      <div className="flex flex-wrap gap-2" role="list">
        {modules.map((module) => (
          <span
            key={module.id}
            role="listitem"
            className={`px-2 py-1 text-[11px] rounded border ${module.enabled ? 'border-emerald-700 bg-emerald-900/30 text-emerald-200' : 'border-neutral-700 bg-neutral-900 text-neutral-400'}`}
            data-testid={`validation-module-${module.id}`}
          >
            {module.label}
            <span className="ml-1 text-[10px] opacity-80">{module.enabled ? 'on' : 'off'}</span>
          </span>
        ))}
      </div>
    </div>
  );
}

// ----- Gating & metadata cards -----
function SignalsCard({ failedChecks, cautionChecks }: { failedChecks: string[]; cautionChecks: string[] }) {
  const hasFailed = failedChecks.length > 0;
  const hasCaution = cautionChecks.length > 0;
  return (
    <article className="border border-neutral-700 rounded p-3 space-y-2" aria-label="Validation checks">
      <header className="text-[12px] font-semibold text-neutral-200">Validation checks</header>
      {!hasFailed && !hasCaution ? (
        <div className="text-[11px] text-neutral-500">All reported validation checks passed.</div>
      ) : (
        <div className="space-y-2 text-[11px]">
          {hasFailed && (
            <div className="bg-rose-900/30 border border-rose-700 text-rose-200 px-2 py-1 rounded" data-testid="validation-failed-checks">
              <div className="font-semibold text-[11px]">Failed</div>
              <ul className="list-disc ml-4 space-y-0.5">
                {failedChecks.map((check) => (
                  <li key={check}>{check}</li>
                ))}
              </ul>
            </div>
          )}
          {hasCaution && (
            <div className="bg-amber-900/30 border border-amber-700 text-amber-100 px-2 py-1 rounded" data-testid="validation-caution-checks">
              <div className="font-semibold text-[11px]">Caution</div>
              <ul className="list-disc ml-4 space-y-0.5">
                {cautionChecks.map((check) => (
                  <li key={check}>{check}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </article>
  );
}

function MetadataCard({ metadata }: { metadata: Record<string, unknown> }) {
  const entries = Object.entries(metadata);
  return (
    <article className="border border-neutral-700 rounded p-3 space-y-2" aria-label="Validation metadata">
      <header className="text-[12px] font-semibold text-neutral-200">Metadata</header>
      {entries.length === 0 ? (
        <div className="text-[11px] text-neutral-500">No additional metadata reported.</div>
      ) : (
        <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-[11px]" data-testid="validation-metadata">
          {entries.map(([key, value]) => (
            <React.Fragment key={key}>
              <dt className="text-neutral-400">{formatMetadataKey(key)}</dt>
              <dd className="text-neutral-100">{renderMetadataValue(value)}</dd>
            </React.Fragment>
          ))}
        </dl>
      )}
    </article>
  );
}

function ArtifactsCard({ artifacts }: { artifacts: ValidationArtifact[] }) {
  return (
    <article className="border border-neutral-700 rounded p-3 space-y-2" aria-label="Validation artifacts">
      <header className="text-[12px] font-semibold text-neutral-200">Validation artifacts</header>
      {artifacts.length === 0 ? (
        <div className="text-[11px] text-neutral-500">No validation artifacts were reported.</div>
      ) : (
        <table className="w-full text-[11px] border border-neutral-700 rounded overflow-hidden" data-testid="validation-artifacts">
          <thead className="bg-neutral-900 text-neutral-300">
            <tr>
              <th className="px-2 py-1 text-left">Path</th>
              <th className="px-2 py-1 text-left">Size</th>
              <th className="px-2 py-1 text-left">SHA-256</th>
            </tr>
          </thead>
          <tbody>
            {artifacts.map((artifact) => (
              <tr key={artifact.path} className="odd:bg-neutral-900/60">
                <td className="px-2 py-1">
                  <a
                    href={`#/artifacts/${encodeURIComponent(artifact.path)}`}
                    className="underline text-sky-300"
                    data-testid={`validation-artifact-${artifact.path}`}
                  >
                    {artifact.path}
                  </a>
                </td>
                <td className="px-2 py-1 text-neutral-300">{formatArtifactSize(artifact.size)}</td>
                <td className="px-2 py-1 font-mono text-[10px] text-neutral-400" title={artifact.sha256 ?? undefined}>
                  {truncateHash(artifact.sha256)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </article>
  );
}

function formatMetadataKey(key: string): string {
  return key.replace(/_/g, ' ');
}

function renderMetadataValue(value: unknown): React.ReactNode {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  try {
    const serialized = JSON.stringify(value, null, 2);
    if (serialized !== undefined) {
      return (
        <pre className="whitespace-pre-wrap break-words bg-neutral-900/70 border border-neutral-700 rounded px-1 py-0.5 text-[10px] text-neutral-300">
          {serialized}
        </pre>
      );
    }
  } catch (error) {
    return String(value);
  }
  return '—';
}

function truncateHash(value?: string | null, length = 12): string {
  if (!value) return '—';
  return value.length <= length ? value : `${value.slice(0, length)}…`;
}

function formatArtifactSize(size?: number | null): string {
  if (size === undefined || size === null || Number.isNaN(size)) return '—';
  const units = ['B', 'KB', 'MB', 'GB'];
  let unitIndex = 0;
  let value = size;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  if (unitIndex === 0) {
    return `${size} ${units[unitIndex]}`;
  }
  return `${value.toFixed(1)} ${units[unitIndex]}`;
}

// ----- Permutation Card -----
interface PermutationCardProps {
  segments: PermutationSegment[];
  significanceThreshold?: number;
}

function PermutationCard({ segments, significanceThreshold }: PermutationCardProps) {
  return (
    <article className="border border-neutral-700 rounded p-3 space-y-2" aria-label="Permutation validation">
      <header className="text-[12px] font-semibold text-neutral-200 flex items-center gap-2">
        Permutation segments
        {typeof significanceThreshold === 'number' && (
          <span className="text-[10px] text-neutral-500">threshold {significanceThreshold.toFixed(3)}</span>
        )}
      </header>
      {segments.length === 0 ? (
        <div className="text-[11px] text-neutral-500">No permutation segments available.</div>
      ) : (
        <ul className="space-y-2" data-testid="validation-permutation-list">
          {segments.map((segment) => {
            const status = getPermutationStatus(segment, significanceThreshold);
            return (
              <li key={segment.segmentId} className="border border-neutral-700 rounded p-2" data-testid={`validation-permutation-${segment.segmentId}`}>
                <div className="flex items-center gap-2 text-[11px] font-medium text-neutral-100">
                  <span>{segment.segmentId}</span>
                  <StatusBadge status={status} />
                </div>
                <dl className="mt-1 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-[11px]">
                  <dt>p-value</dt>
                  <dd>{formatNumber(segment.pValue)}</dd>
                  <dt>Effect size</dt>
                  <dd>{formatNumber(segment.effectSize)}</dd>
                  {segment.observedMetric !== undefined && (
                    <>
                      <dt>Observed metric</dt>
                      <dd>{formatNumber(segment.observedMetric)}</dd>
                    </>
                  )}
                  <dt>Executed</dt>
                  <dd>{segment.executedPermutations ?? '—'}</dd>
                  {typeof segment.requestedPermutations === 'number' && (
                    <>
                      <dt>Requested</dt>
                      <dd>{segment.requestedPermutations}</dd>
                    </>
                  )}
                </dl>
                {segment.fallbackReason && (
                  <div className="mt-1 text-[10px] text-amber-400" data-testid={`validation-permutation-fallback-${segment.segmentId}`}>
                    Fallback: {segment.fallbackReason.replace(/_/g, ' ')}
                  </div>
                )}
                {segment.histogramSummary && (
                  <div className="mt-2">
                    <HistogramSummary summary={segment.histogramSummary} />
                  </div>
                )}
                {segment.artifactPath && (
                  <div className="mt-2 text-[10px]">
                    <a
                      href={`#/artifacts/${encodeURIComponent(segment.artifactPath)}`}
                      className="underline text-sky-300"
                      data-testid={`validation-permutation-artifact-${segment.segmentId}`}
                    >
                      artifact
                    </a>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </article>
  );
}

function getPermutationStatus(segment: PermutationSegment, significanceThreshold?: number): ValidationStatus {
  if (typeof significanceThreshold !== 'number' || segment.pValue === undefined) {
    return 'unknown';
  }
  return segment.pValue <= significanceThreshold ? 'pass' : 'caution';
}

function HistogramSummary({ summary }: { summary: NonNullable<PermutationSegment['histogramSummary']> }) {
  const { mean, stdDev, percentiles } = summary;
  return (
    <div className="text-[10px] bg-neutral-900/60 border border-neutral-700 rounded p-2">
      <div className="font-semibold text-neutral-300">Histogram summary</div>
      <div className="grid grid-cols-[auto_1fr] gap-x-2 gap-y-1 mt-1">
        <span>mean</span><span>{formatNumber(mean)}</span>
        <span>std dev</span><span>{formatNumber(stdDev)}</span>
      </div>
      {percentiles.length > 0 && (
        <div className="mt-2">
          <div className="font-semibold text-neutral-300">percentiles</div>
          <ul className="grid grid-cols-3 gap-1 mt-1">
            {percentiles.map((p) => (
              <li key={p.percentile} className="bg-neutral-800/70 rounded px-1 py-0.5 text-center">
                <span className="block text-[9px] text-neutral-500">p{p.percentile}</span>
                <span>{formatNumber(p.value)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// ----- Bias Adjustments -----
function BiasAdjustmentsCard({ data }: { data?: BiasAdjustments }) {
  return (
    <article className="border border-neutral-700 rounded p-3 space-y-2" aria-label="Bias adjustments">
      <header className="flex items-center gap-2 text-[12px] font-semibold text-neutral-200">
        Bias adjustments
        <StatusBadge status={data?.status ?? 'unknown'} />
      </header>
      {!data ? (
        <div className="text-[11px] text-neutral-500">No bias adjustment metrics reported.</div>
      ) : (
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-[11px]">
          <dt>Observed Sharpe</dt>
          <dd>{formatNumber(data.observedSharpe)}</dd>
          <dt>Deflated Sharpe</dt>
          <dd>{formatNumber(data.deflatedSharpe)}</dd>
          <dt>Prob. Sharpe</dt>
          <dd>{formatNumber(data.probabilisticSharpe)}</dd>
          <dt>Trials</dt>
          <dd>{data.assumedTrials ?? '—'}</dd>
          <dt>Benchmark</dt>
          <dd>{formatNumber(data.benchmarkSharpe)}</dd>
          <dt>Skewness</dt>
          <dd>{formatNumber(data.skewness)}</dd>
          <dt>Kurtosis</dt>
          <dd>{formatNumber(data.kurtosis)}</dd>
        </dl>
      )}
    </article>
  );
}

// ----- Cross Validation -----
function CrossValidationCard({ data, leakageThreshold }: { data?: CrossValidationSection; leakageThreshold?: number }) {
  return (
    <article className="border border-neutral-700 rounded p-3 space-y-2" aria-label="Cross-validation">
      <header className="flex items-center gap-2 text-[12px] font-semibold text-neutral-200">
        Cross-validation
        <StatusBadge status={deriveCrossValidationStatus(data, leakageThreshold)} />
      </header>
      {!data ? (
        <div className="text-[11px] text-neutral-500">No cross-validation results.</div>
      ) : (
        <div className="space-y-2">
          <div className="flex flex-wrap gap-2 text-[11px] text-neutral-300">
            {data.mode && <span>Mode: {data.mode}</span>}
            {typeof data.leakageScore === 'number' && (
              <span data-testid="validation-leakage-score">
                Leakage score: {data.leakageScore.toFixed(3)}
              </span>
            )}
            {typeof leakageThreshold === 'number' && (
              <span className="text-neutral-500">threshold {leakageThreshold.toFixed(2)}</span>
            )}
          </div>
          <table className="w-full text-[11px] border border-neutral-700 rounded overflow-hidden" data-testid="validation-fold-table">
            <thead className="bg-neutral-900 text-neutral-300">
              <tr>
                <th className="px-2 py-1 text-left">Fold</th>
                <th className="px-2 py-1 text-left">Train</th>
                <th className="px-2 py-1 text-left">Test</th>
                <th className="px-2 py-1 text-left">Purge</th>
                <th className="px-2 py-1 text-left">Metrics</th>
              </tr>
            </thead>
            <tbody>
              {data.folds.map((fold) => (
                <tr key={fold.foldId} className="odd:bg-neutral-900/60">
                  <td className="px-2 py-1 font-medium text-neutral-100">{fold.foldId}</td>
                  <td className="px-2 py-1 text-neutral-400">{formatRange(fold.trainRange)}</td>
                  <td className="px-2 py-1 text-neutral-400">{formatRange(fold.testRange)}</td>
                  <td className="px-2 py-1 text-neutral-400">{fold.purgeSpan ?? '—'}</td>
                  <td className="px-2 py-1 text-neutral-300">
                    {Object.keys(fold.metrics).length === 0 ? (
                      <span className="text-neutral-500">—</span>
                    ) : (
                      <div className="flex flex-wrap gap-1">
                        {Object.entries(fold.metrics).map(([key, value]) => (
                          <span key={key} className="px-1 py-0.5 bg-neutral-800 rounded">
                            {key}: {formatNumber(value)}
                          </span>
                        ))}
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </article>
  );
}

function deriveCrossValidationStatus(data?: CrossValidationSection, leakageThreshold?: number): ValidationStatus {
  if (!data) return 'unknown';
  if (data.biasFlag) return 'caution';
  if (typeof data.leakageScore === 'number' && typeof leakageThreshold === 'number') {
    return data.leakageScore > leakageThreshold ? 'caution' : 'pass';
  }
  return 'pass';
}

function formatRange(range?: { start?: string; end?: string }): string {
  if (!range) return '—';
  const start = range.start ?? '…';
  const end = range.end ?? '…';
  return `${start} → ${end}`;
}

// ----- Execution Realism -----
function ExecutionRealismCard({ data, capacityLimitBps }: { data?: ExecutionRealismSection; capacityLimitBps?: number }) {
  return (
    <article className="border border-neutral-700 rounded p-3 space-y-2" aria-label="Execution realism">
      <header className="flex items-center gap-2 text-[12px] font-semibold text-neutral-200">
        Execution realism
        <StatusBadge status={data?.status ?? 'unknown'} />
      </header>
      {!data ? (
        <div className="text-[11px] text-neutral-500">No execution realism diagnostics reported.</div>
      ) : (
        <div className="space-y-2 text-[11px]">
          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
            <dt>Transaction cost (bps)</dt>
            <dd>{formatNumber(data.transactionCostBps)}</dd>
            <dt>Impact (bps)</dt>
            <dd>{formatNumber(data.marketImpactBps)}</dd>
            <dt>Capacity ratio</dt>
            <dd>
              {formatNumber(data.capacityRatio)}
              {typeof capacityLimitBps === 'number' && ' '}
              {typeof capacityLimitBps === 'number' && (
                <span className="text-neutral-500">(limit {capacityLimitBps}bps)</span>
              )}
            </dd>
          </dl>
          {data.warnings.length > 0 && (
            <div className="bg-amber-900/40 border border-amber-700 text-amber-200 px-2 py-1 rounded" data-testid="validation-realism-warnings">
              <div className="font-semibold text-[11px]">Warnings</div>
              <ul className="list-disc ml-4">
                {data.warnings.map((warning, idx) => (
                  <li key={idx}>{warning}</li>
                ))}
              </ul>
            </div>
          )}
          {data.guidance.length > 0 && (
            <div className="bg-sky-900/30 border border-sky-800 text-sky-200 px-2 py-1 rounded" data-testid="validation-realism-guidance">
              <div className="font-semibold text-[11px]">Guidance</div>
              <ul className="list-disc ml-4">
                {data.guidance.map((item, idx) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
            </div>
          )}
          {Object.keys(data.assumptions).length > 0 && (
            <div className="text-[10px] text-neutral-400" data-testid="validation-realism-assumptions">
              <div className="font-semibold text-neutral-300">Assumptions</div>
              <ul className="grid grid-cols-2 gap-1 mt-1">
                {Object.entries(data.assumptions).map(([key, value]) => (
                  <li key={key} className="bg-neutral-900/60 px-1 py-0.5 rounded">
                    <span className="text-neutral-500 mr-1">{key}</span>
                    <span>{String(value)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </article>
  );
}

// ----- Utilities -----
function formatNumber(value?: number | null): string {
  if (value === undefined || value === null || Number.isNaN(value)) return '—';
  if (Math.abs(value) >= 100 || Math.abs(value) < 0.001) {
    return value.toExponential(2);
  }
  return value.toFixed(3);
}
